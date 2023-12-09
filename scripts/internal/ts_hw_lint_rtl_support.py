# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square
# Functions for ts_dft_run.py

#
# For license see LICENSE file in repository root.
####################################################################################################


import logging
import os
import pty
import select
import shutil
import subprocess
import termios
import tty
from datetime import datetime

from .ts_grammar import ALLOWED_DESIGN_OBJ_TYPES
from .ts_hw_cfg_parser import parse_runcode_arg_root_dir
from .ts_hw_common import (
    get_env_var_path,
    get_pdk_corners,
    get_pdk_obj,
    get_repo_root_path,
    ts_get_cfg,
    ts_get_curr_dir_rel_path,
    ts_get_design_top,
    ts_get_root_rel_path,
    ts_set_env_var,
    view_has_corner,
)
from .ts_hw_design_config_file import check_export_view_types
from .ts_hw_export import export_design_config, export_spyglass_src_file
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsColors,
    TsErrCode,
    TSFormatter,
    TsInfoCode,
    TsWarnCode,
    ts_info,
    ts_print,
    ts_throw_error,
    ts_warning,
)


def rtl_lint_logging(args):
    """
    Configures additional handler for logging flow file log
    :args: Argparse command line arguments object.
    """

    # Get existing logger
    logger = logging.getLogger()
    # Create time stamp for a log file name
    date_time = datetime.now()
    # Set full path and a name of the log file
    os.makedirs(TsGlobals.TS_RTL_LINT_LOGS_DIR, exist_ok=True)
    filename = f'{TsGlobals.TS_RTL_LINT_LOGS_DIR}/{args.runcode}_{date_time.strftime("%y%m%d.%H%M%S")}.log'
    handler = logging.FileHandler(filename)
    handler.setFormatter(TSFormatter(use_colors=False))
    logger.addHandler(handler)


def set_rtl_lint_global_vars(args):
    """
    Set RTL LINT flow global variables
    """
    # Check runcode validity and update it if the _n+1 rule is applicable
    # Set synthesis run dir according to runcode
    TsGlobals.TS_RTL_LINT_RUNCODE = parse_runcode_arg_root_dir(args, get_rootdir(args))
    TsGlobals.TS_RTL_LINT_RUN_DIR = os.path.join(
        get_rootdir(args), TsGlobals.TS_RTL_LINT_RUNCODE
    )

    # Set sythesis dirs for purpose of the run
    TsGlobals.TS_RTL_LINT_LOGS_DIR = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, TsGlobals.TS_RTL_LINT_LOGS_DIR
    )
    TsGlobals.TS_RTL_LINT_RESULTS_DIR = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, TsGlobals.TS_RTL_LINT_RESULTS_DIR
    )
    TsGlobals.TS_RTL_LINT_REPORTS_DIR = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, TsGlobals.TS_RTL_LINT_REPORTS_DIR
    )
    # Setting path for running LINT
    TsGlobals.TS_RTL_LINT_RUNFILE = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, TsGlobals.TS_RTL_LINT_RUNFILE
    )
    # Setting build dir for rtl sub-blocks compilation
    TsGlobals.TS_RTL_LINT_BUILD_DIR = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, "build"
    )

    # Setting design_cfg file path and name
    TsGlobals.TS_RTL_LINT_DESIGN_CFG_FILE = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, TsGlobals.TS_RTL_LINT_DESIGN_CFG_FILE
    )

    # Setting source file path and name
    TsGlobals.TS_RTL_LINT_SRC_RTL_FILE = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, TsGlobals.TS_RTL_LINT_SRC_RTL_FILE
    )

    # LINT setup file path
    TsGlobals.TS_RTL_LINT_SETUP_FILE = os.path.join(
        TsGlobals.TS_RTL_LINT_RUN_DIR, TsGlobals.TS_RTL_LINT_SETUP_FILE
    )


def get_rootdir(args):
    """
    Get LINT root dir according to flow type
    """
    # Structure according to agreement with O.Ille
    root_dir = f"{get_repo_root_path()}/lint/{TsGlobals.TS_RTL_LINT_TOOL}"
    return root_dir


def create_rtl_lint_subdirs():
    """
    Create directory structure for LINT
    """
    # Main runcode subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_RTL_LINT_RUN_DIR)
    os.makedirs(TsGlobals.TS_RTL_LINT_RUN_DIR, exist_ok=True)
    # Logs subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_RTL_LINT_LOGS_DIR)
    os.makedirs(TsGlobals.TS_RTL_LINT_LOGS_DIR, exist_ok=True)
    # Results subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_RTL_LINT_RESULTS_DIR)
    os.makedirs(TsGlobals.TS_RTL_LINT_RESULTS_DIR, exist_ok=True)
    # Report subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_RTL_LINT_REPORTS_DIR)
    os.makedirs(TsGlobals.TS_RTL_LINT_REPORTS_DIR, exist_ok=True)
    # Build subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_RTL_LINT_BUILD_DIR)
    os.makedirs(TsGlobals.TS_RTL_LINT_BUILD_DIR, exist_ok=True)


def delete_rtl_lint_subdirs():
    """
    Delete directiories in run folder.

    """
    ts_info(TsInfoCode.INFO_SYS_5, TsGlobals.TS_RTL_LINT_RUN_DIR)
    shutil.rmtree(TsGlobals.TS_RTL_LINT_RUN_DIR, ignore_errors=True)


def lint_src_file():
    """
    Generates target RTL LINT TCL script(s)
    * Executes the ts_sim_compile.load_source_list_files that prepared data for export
    * This assumes that you have RTL target (--exp-tcl-file-spyglass) defined in your *IP/sim/ts_sim_cfg.yml as ts_sim_config.yml

    """
    # Currently supported only 'export_spyglass_src_files'
    path = f"{TsGlobals.TS_RTL_LINT_SRC_RTL_FILE}"
    cmd = f'export_{TsGlobals.TS_RTL_LINT_TOOL}_src_file("{path}")'
    try:
        exec(cmd)
    except KeyError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Not defined ts_hw_dft_support.{cmd} for selected LINT tool {TsGlobals.TS_RTL_LINT_TOOL}",
        )


# Generic LINT cmd tool regardless
def build_lint_cmd(args):
    """
    Returns tool command for dft lint
    """
    cmd = f"build_{TsGlobals.TS_RTL_LINT_TOOL}_cmd(args)"
    try:
        return eval(cmd)
    except KeyError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Not defined ts_hw_dft_support.build_{TsGlobals.TS_RTL_LINT_TOOL}_cmd() for selected LINT tool {TsGlobals.TS_RTL_LINT_TOOL}",
        )


# LINT cmd spyglass tool
def build_spyglass_cmd(args):
    """
    Returns spyglass command for execution by ts-commonexec_cmd_in_dir_interactive()
    This is tricky because interactive shell runs sg_shell for new project generation and then runs spyglass explorer to see results
    """
    # Runs sg_shell
    sg_cfg_args = f"-64bit "
    sg_cfg_args += f"-tcl {TsGlobals.TS_RTL_LINT_RUNFILE} "
    sg_cmd = f'TERM=xterm /usr/bin/bash -c "cd {TsGlobals.TS_RTL_LINT_RUN_DIR}; sg_shell {sg_cfg_args}" ;'

    # Runs spyglass Explorer
    if args.gui:
        sg_cfg_args = f"-64bit "
        sg_cfg_args += f"-project {TsGlobals.TS_RTL_LINT_RUNCODE}.prj "
        sg_cmd += f"spyglass {sg_cfg_args}"

    return sg_cmd


# Generic RTL LINT RUN FILE tool regardless
def rtl_lint_runfile(args):
    """
    Returns runfile
    """
    cmd = f"rtl_lint_runfile_{TsGlobals.TS_RTL_LINT_TOOL}(args)"
    try:
        return eval(cmd)
    except KeyError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Not defined ts_hw_dft_support.dft_runfile_{TsGlobals.TS_RTL_LINT_TOOL}(args) for selected LINT tool {TsGlobals.TS_RTL_LINT_TOOL}",
        )


# LINT SPYGLASS RTL RUNFILE (project file)
def rtl_lint_runfile_spyglass(args):
    """
    Generates main dft batch runfile for spyglass (a project file in spyglass terminology)
    * Imports all generated files
    * Imports project/IP specific settings files
    * Imports spyglass constraint file
    """
    # File location
    path = f"{TsGlobals.TS_RTL_LINT_RUNFILE}"
    # File content
    lines = []
    # Initial settings
    lines.append(f"new_project {TsGlobals.TS_RTL_LINT_RUNCODE} -projectwdir . \n")
    lines.append(f"set_option sort yes\n")
    lines.append(f"set_option enableSV09 yes\n")
    lines.append(f"set_option hdlin_translate_off_skip_text yes\n")
    lines.append(f"set_option pragma {{synthesis}}\n")
    lines.append(f"set_option pragma {{translate}}\n")
    lines.append(f"set_option define {{TS_MBIST}}\n")
    # Waver
    # lines.append(f"waive -rule ErrorAnalyzeBBox\n")
    # Sourcing files and libraries
    lines.append(f"source {TsGlobals.TS_RTL_LINT_DESIGN_CFG_FILE}\n")
    lines.append(f"read_file -type sglib {TsGlobals.TS_RTL_LINT_BUILD_DIR}/*.sglib\n")
    lines.append(f"source {TsGlobals.TS_RTL_LINT_SRC_RTL_FILE}\n")
    # Ignore problematic file - to be removed/fixed
    # lines.append(
    #    f"set_option ignorefile /projects/tropic01/work/{os.getenv('USER')}/ts-common-blocks/rtl/sv/tr_maj_edet_reg_vect.sv\n"
    # )
    # Constraints
    lines.append(f"read_file -type sgdc {TsGlobals.TS_RTL_LINT_CONSTRAINT}\n")
    # Compile
    lines.append(f"compile_design -force\n")
    lines.append(f"\n")

    # Set goal
    lines.append(
        f"current_goal lint/lint_rtl -top {str(ts_get_design_top()).lower()}\n"
    )
    # Run goal
    lines.append(f"run_goal\n")

    # Set goal
    lines.append(
        f"current_goal lint/lint_rtl_enhanced -top {str(ts_get_design_top()).lower()}\n"
    )
    lines.append(f"run_goal\n")

    lines.append(
        f"current_goal lint/lint_turbo_rtl -top {str(ts_get_design_top()).lower()}\n"
    )
    lines.append(f"run_goal\n")

    lines.append(
        f"current_goal lint/lint_functional_rtl -top {str(ts_get_design_top()).lower()}\n"
    )
    lines.append(f"run_goal\n")

    lines.append(
        f"current_goal lint/lint_abstract -top {str(ts_get_design_top()).lower()}\n"
    )
    lines.append(f"run_goal\n")

    # Save and exit
    lines.append(f"save_project\n")
    lines.append(f"close_project\n")
    lines.append(f"exit\n")

    # Create and write the file
    with open(path, "w") as dft_runfile:
        dft_runfile.writelines(lines)


# Generic lint design file
def lint_design_cfg(args):
    """
    Returns cfg file
    """
    cmd = f"lint_design_cfg_{TsGlobals.TS_RTL_LINT_TOOL}(args)"
    try:
        return eval(cmd)
    except KeyError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Not defined ts_hw_dft_support.lint_design_cfg_{TsGlobals.TS_RTL_LINT_TOOL}(args) for selected LINT tool {TsGlobals.TS_RTL_LINT_TOOL}",
        )


# LINT SPYGLASS DESIGN CFG FILE
def lint_design_cfg_spyglass(args):
    """
    Generates design configuration TCL script
    * Executes selected procedures from ts_design_cfg script
    * Generated file to be stored in TS_RTL_LINT_RUN_DIR directory
    """

    setattr(
        args,
        "add_top_entity",
        TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_DESIGN_CFG["design"]["target"]][
            "top_entity"
        ],
    )
    add_topo_data = False

    setattr(args, "add_floorplan", add_topo_data)
    setattr(args, "add_tluplus", add_topo_data)
    setattr(args, "add_map_tech", add_topo_data)

    setattr(args, "add_spef", False)
    setattr(args, "add_wireload", True)
    setattr(args, "add_opcond", True)

    views_to_add = "nldm_db"
    setattr(args, "add_views", views_to_add)
    TsGlobals.TS_EXP_VIEWS = args.add_views.split(",")

    setattr(args, "add_syn_rtl_build_dirs", False)
    setattr(args, "add_constraints", False)

    # ts_hw_design_config_file used in ts_design_cfg.py
    check_export_view_types(args)

    # ts_hw_design_config_file used in ts_design_cfg.py
    export_design_config(TsGlobals.TS_RTL_LINT_DESIGN_CFG_FILE, args)


# Generic lint setup file
def lint_setup_file(args):
    """
    Returns setup file
    """
    cmd = f"lint_setup_file_{TsGlobals.TS_RTL_LINT_TOOL}()"
    try:
        return eval(cmd)
    except KeyError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Not defined ts_hw_dft_support.lint_setup_file_{TsGlobals.TS_RTL_LINT_TOOL}(args) for selected LINT tool {TsGlobals.TS_RTL_LINT_TOOL}",
        )


def lint_setup_file_spyglass():
    """
    Generates spyglass_lc commands for literty files compilation to *.sglib
    """

    # Build lists for the views
    view = "nldm_lib"
    cmd = ""

    for obj_type in ALLOWED_DESIGN_OBJ_TYPES:
        if obj_type in TsGlobals.TS_DESIGN_CFG["design"]:
            val = TsGlobals.TS_DESIGN_CFG["design"][obj_type]
            for target_obj in val:
                assert type(target_obj) == dict
                target_obj_name = list(target_obj.keys())[0]
                target_obj_version = list(target_obj.values())[0]

                obj = get_pdk_obj(obj_type, target_obj_name, target_obj_version)
                if view not in obj["views"]:
                    if enforce:
                        ts_throw_error(
                            TsErrCode.ERR_PDK_25,
                            target_obj_name,
                            target_obj_version,
                            vnt_rtl_run.py - hiew,
                        )
                    else:
                        ts_warning(
                            TsWarnCode.WARN_PDK_3,
                            target_obj_name,
                            target_obj_version,
                            view,
                        )
                    continue

                for mode in TsGlobals.TS_DESIGN_CFG["design"]["modes"]:
                    if mode["corner"] not in obj["views"][view]:
                        ts_warning(
                            TsWarnCode.WARN_PDK_4,
                            target_obj_name,
                            target_obj_version,
                            view,
                            mode["corner"],
                        )
                        continue
                    cmd += f"spyglass_lc -64bit -gateslib {obj['views'][view][mode['corner']]} -wdir {TsGlobals.TS_RTL_LINT_BUILD_DIR};"

    return cmd


# Generic lint open design
def open_design(args):
    """
    Returns open design command to be run
    """

    cmd = f"{args.flow}_{TsGlobals.TS_RTL_LINT_TOOL}_open_design(args)"

    try:
        return eval(cmd)
    except KeyError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Not defined ts_hw_dft_support.{cmd}",
        )


# Lint RTL spyglass open design command
def rtl_lint_spyglass_open_design(args):

    # Runs spyglass Explorer
    sg_cfg_args = f"-64bit "
    sg_cfg_args += f"-project {TsGlobals.TS_RTL_LINT_RUNCODE}.prj "

    sg_cmd = f"spyglass {sg_cfg_args}"
    sg_cmd = (
        f'TERM=xterm /usr/bin/bash -c "cd {TsGlobals.TS_RTL_LINT_RUN_DIR}; {sg_cmd}" ;'
    )

    return sg_cmd
