#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square
# Functions for ts_sta_run.py
#
# For license see LICENSE file in repository root.
####################################################################################################


import logging
import os
import shutil
from datetime import datetime

from .ts_hw_cfg_parser import parse_runcode_arg
from .ts_hw_common import (
    get_env_var_path,
    get_repo_root_path,
    ts_get_design_top,
    ts_get_root_rel_path,
)
from .ts_hw_design_config_file import check_export_view_types
from .ts_hw_export import export_design_config
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsColors,
    TsErrCode,
    TSFormatter,
    TsInfoCode,
    ts_debug,
    ts_info,
    ts_print,
    ts_throw_error,
)


def set_sta_global_vars(args):
    """
    Set static timing analysis flow global variables
    """
    # Check runcode validity and update it if the _n+1 rule is applicable
    TsGlobals.TS_STA_RUNCODE = parse_runcode_arg(args)
    # Set synthesis run dir according to runcode
    TsGlobals.TS_STA_RUN_DIR = get_sta_rundir(TsGlobals.TS_STA_RUNCODE)
    # Set sythesis dirs for purpose of the run
    TsGlobals.TS_STA_LOGS_DIR = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_LOGS_DIR
    )
    TsGlobals.TS_STA_RESULTS_DIR = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_RESULTS_DIR
    )
    TsGlobals.TS_STA_REPORTS_DIR = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_REPORTS_DIR
    )
    # Setting paths for open synthesis database
    TsGlobals.TS_STA_DC_RM_OPENFILE = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_DC_RM_OPENFILE
    )
    # Setting path for run sythesis
    TsGlobals.TS_STA_DC_RM_RUNFILE = os.path.join(
        get_env_var_path(TsGlobals.TS_STA_FLOW_PATH), TsGlobals.TS_STA_DC_RM_RUNFILE
    )
    # Setting synthesis build dir for rtl sub-blocks compilation
    TsGlobals.TS_STA_BUILD_DIR = os.path.join(TsGlobals.TS_STA_RUN_DIR, "build")
    # Setting design_cfg file path and name
    TsGlobals.TS_STA_DESIGN_CFG_FILE = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_DESIGN_CFG_FILE
    )
    # Setting DMSA setup file path and name
    TsGlobals.TS_STA_DMSA_FILE = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_DMSA_FILE
    )
    # Setting the netlist
    if not args.open_result:
        TsGlobals.TS_STA_DC_RM_NETLIST = __sta_netlist_selection(args)
    # STA setup file path
    TsGlobals.TS_STA_SETUP_FILE = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_SETUP_FILE
    )
    # STA DMSA file path
    TsGlobals.TS_STA_DMSA_FILE = os.path.join(
        TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_DMSA_FILE
    )


def create_sta_sub_dirs():
    """
    Create directorie structure in "TS_REPO_ROOT/sta/<runcode>" folder.
    """
    # Main runcode subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_STA_RUN_DIR)
    os.makedirs(TsGlobals.TS_STA_RUN_DIR, exist_ok=True)
    # Logs subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_STA_LOGS_DIR)
    os.makedirs(TsGlobals.TS_STA_LOGS_DIR, exist_ok=True)
    # Results subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_STA_RESULTS_DIR)
    os.makedirs(TsGlobals.TS_STA_RESULTS_DIR, exist_ok=True)
    # Report subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_STA_REPORTS_DIR)
    os.makedirs(TsGlobals.TS_STA_REPORTS_DIR, exist_ok=True)


def delete_sta_sub_dir():
    """
    Delete "TS_REPO_ROOT/sta/<runcode>" folder completely
    """
    ts_info(TsInfoCode.INFO_SYS_5, TsGlobals.TS_STA_RUN_DIR)
    shutil.rmtree(TsGlobals.TS_STA_RUN_DIR, ignore_errors=True)


def get_sta_rundir(runcode: str):
    """
    Returns full path of sta directory
    """
    return f"{get_repo_root_path()}/sta/{runcode}"


def runcode_dir_test(args):
    """
    Returns True or False of runcode directory existance test
    """
    path = f"{get_repo_root_path()}/sta/{args.runcode}"
    ts_debug(f"Testing folder {path}")
    return os.path.isdir(path)


def build_sta_cmd(args):
    """
    Builds command for pt_shell
    """

    # Fixed structure of Primetime STA flow
    pt_cfg_args = f""

    # Select between either opening of design or running new sythesis
    if args.open_result:
        # Path to DC_RM_OPENFILE
        pt_cfg_args += f"-f {TsGlobals.TS_STA_DC_RM_OPENFILE} "
    else:
        # Path DC_RM_RUNFILE
        if args.dmsa:
            pt_cfg_args += f"-multi_scenario -f {os.path.join(TsGlobals.TS_STA_RUN_DIR,TsGlobals.TS_STA_DMSA_FILE)} "
        else:
            pt_cfg_args += f"-f {TsGlobals.TS_STA_DC_RM_RUNFILE} "

    # LOG FILE
    logfile = f"{TsGlobals.TS_STA_LOGS_DIR}/{TsGlobals.TS_STA_RUNCODE}_sta"
    if args.open_result:
        logfile += "_open{}".format(datetime.now().strftime("_%Y_%m_%d_%H_%M_%S_%f"))
    logfile += ".log"

    if not args.checker:
        pt_cfg_args += f"-output_log {logfile} "
    else:
        pt_cfg_args += f"-constraints "

    # GIT SHA CMD
    git_cmd = f"`git log --pretty=format:'%H' -n 1`"

    # List of all variables used for synthesis flow that is passed as a single dc_shell command
    pt_cfg_args += f'-x \\"set SIGNOFF {args.sign_off};'
    if args.mode:
        pt_cfg_args += f"set MODE {str(args.mode).upper()};"
    pt_cfg_args += (
        f'set REPORT_POSTPROC "false"; set RUNCODE_CMD_LINE {TsGlobals.TS_STA_RUNCODE};'
    )
    pt_cfg_args += f"set RESULTS_DIR {TsGlobals.TS_STA_RESULTS_DIR};set REPORTS_DIR {TsGlobals.TS_STA_REPORTS_DIR};set DMSA {args.dmsa};"
    pt_cfg_args += f'set GIT_COMMIT_SHA {git_cmd};cd {TsGlobals.TS_STA_RUN_DIR};set STAYIN {args.stay_in_tool}; set SDC_EXPORT {args.sdc_export}\\"'

    # Final dc_shell command completition
    pt_cmd = f'TERM=xterm /usr/bin/bash -c "pt_shell {pt_cfg_args}" '

    # Stash standrard output if configured
    if args.no_std_out:
        pt_cmd = f'{pt_cmd} >> /dev/null'

    # Report final dc_cmd
    ts_info(TsInfoCode.INFO_SYS_3, "pt_shell", pt_cmd)

    return [pt_cmd, logfile]


def sta_logging(args):
    """
    Configures additional handler for logging sta file log
    :args: Argparse command line arguments object.
    """

    # Get existing logger
    logger = logging.getLogger()
    # Create time stamp for a log file name
    date_time = datetime.now()
    # Set full path and a name of the log file
    os.makedirs(TsGlobals.TS_STA_LOGS_DIR, exist_ok=True)
    filename = f'{TsGlobals.TS_STA_LOGS_DIR}/{TsGlobals.TS_STA_RUNCODE}_{date_time.strftime("%y%m%d.%H%M%S")}.log'
    handler = logging.FileHandler(filename)
    handler.setFormatter(TSFormatter(use_colors=False))
    logger.addHandler(handler)


def sta_design_cfg_file(args):
    """
    Generates design configuration TCL script
    * Executes selected procedures from ts_design_cfg script
    * Generated file to be stored in TS_STA_RUN_DIR directory
    """
    # adds argumens used with check_export_view_types and export_design_config procedures
    setattr(args, "add_views", "nldm_db,ccs_db,lef,milkyway")
    setattr(
        args,
        "add_top_entity",
        TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_DESIGN_CFG["design"]["target"]][
            "top_entity"
        ],
    )
    setattr(args, "add_syn_rtl_build_dirs", False)
    setattr(args, "add_constraints", True)
    setattr(args, "add_floorplan", False)
    setattr(args, "add_spef", True)
    setattr(args, "add_tluplus", False)
    setattr(args, "add_map_tech", False)
    setattr(args, "add_wireload", True)
    setattr(args, "add_opcond", False)

    TsGlobals.TS_EXP_VIEWS = args.add_views.split(",")
    # ts_hw_design_config_file used in ts_design_cfg.py
    check_export_view_types(args)
    # ts_hw_design_config_file used in ts_design_cfg.py
    export_design_config(TsGlobals.TS_STA_DESIGN_CFG_FILE, args)


def sta_dmsa_file(path: str, args):
    """
    Generates DCRM_DMSA_SCENARIOS_SETUP_FILE - bridge file between pdk cfg, design cfg, sim cfg and synthesis flow to support mcmm methodology
    : param path: path where to generate the file + name of the file
    : param args: arguments

    """
    # Modes
    modes = TsGlobals.TS_DESIGN_CFG["design"]["modes"]

    # Empty buffer - generation to be line by line
    lines = []

    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"# DMSA scenarios setup file\n")
    lines.append(f"# Script: {TsGlobals.TS_STA_DMSA_FILE}\n")
    lines.append(f"# Version: R-2021.04-SP3\n")
    lines.append(f"# Copyright (C) Tropic Square. All rights reserved.\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    lines.append(f'set multi_scenario_working_directory "./"\n')
    lines.append(f'set multi_scenario_merged_error_log "merged_errors.log"\n')
    lines.append(f"\n")
    lines.append(f"set_host_option -num_processes 1\n")
    lines.append(f"start_hosts\n")
    lines.append(f"\n")
    lines.append(f"\n")

    # Create list of modes
    if modes is not None:
        lines.append(f"set MODES [dict create]\n\n")

    for mode in modes:
        lines.append(f"dict set MODES {mode['name'].upper()} {{ \n")

        for key in mode:
            lines.append(f" {key} {mode[key]} \n")

        lines.append(f"}}\n\n")
    lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f"foreach MODE [dict keys $MODES] {{\n")
    lines.append(f"\n")
    lines.append(
        f"     create_scenario -mode [dict get $MODES $MODE name] -corner [dict get $MODES $MODE corner] -common_variables {{MODE SDC_EXPORT STAYIN RUNCODE_CMD_LINE SIGNOFF REPORTS_DIR RESULTS_DIR DMSA}} -common_data {TsGlobals.TS_STA_DC_RM_RUNFILE}\n"
    )
    lines.append(f"}}\n")
    lines.append(f"\n")
    lines.append(f"current_session -all\n")
    lines.append(f"remote_execute {{update_timing}}\n")
    lines.append(f"\n")
    lines.append(f"save_session {str(ts_get_design_top()).lower()}_ss\n")
    lines.append(f"\n")
    lines.append(f"unset MODES\n")
    lines.append(f"\n")
    lines.append(f"if {{ !$STAYIN }} {{exit}}\n")
    lines.append(f"\n")

    # Create and write
    with open(path, "w") as setup_file:
        setup_file.writelines(lines)


def sta_setup(path: str, args):
    """
    Generates ts_sta_setup file - bridge between pdk cfg, design cfg, sim cfg and sta flow
    : param path: path where to generate the file + name of the file
    : param args: arguments
    """
    # Modes
    modes = TsGlobals.TS_DESIGN_CFG["design"]["modes"]

    # Empty buffer - generation to be line by line
    lines = []

    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"# Variables common to all reference methodology scripts\n")
    lines.append(f"# Script: {TsGlobals.TS_STA_SETUP_FILE}\n")
    lines.append(f"# Version: R-2020.09-SP4\n")
    lines.append(f"# Copyright (C) Tropic Square. All rights reserved.\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    # Entry point for usage auto-generated design.tcl
    lines.append(f"source -echo -verbose {TsGlobals.TS_STA_DESIGN_CFG_FILE}\n")
    lines.append(f"# The name of top level design\n")
    lines.append(f'set DESIGN_NAME "{str(ts_get_design_top()).lower()}"\n')
    lines.append(f"\n")
    lines.append(
        "##########################################################################################\n"
    )
    lines.append("# Library Setup Variables\n")

    lines.append(f"set MODES [dict create]\n\n")


    for mode in modes:
        lines.append(f"dict set MODES {mode['name'].upper()} {{ \n")
    # Python list to TCL list if necessary
    # This is needed for usage list
        for key in mode:
            if type(mode[key]) is list:
                lines.append(f" {key} {{{' '.join(map(str,mode[key]))}}} \n")
            else:
                lines.append(f" {key} {mode[key]} \n")
        lines.append(f"}}\n\n")


    lines.append(f"\n")
    lines.append(
        f"set ADDITIONAL_SEARCH_PATH [concat ${{TS_NLDM_DB_VIEW_DIRS}} ${{TS_CCS_DB_VIEW_DIRS}}] \n"
    )
    lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f"# Target library\n")
    lines.append(f'set TARGET_LIBRARY_FILES_STA ""\n')
    lines.append(f"\n")
    # lines.append(f'foreach MODE [dict keys $MODES] {{\n')
    lines.append(
        f" set TARGET_LIBRARY_FILES_STA [concat [set TARGET_LIBRARY_FILES_STA] [set TS_NLDM_DB_[set MODE]_VIEWS]] \n"
    )
    # lines.append(f'}}\n')
    lines.append(f"\n")
    lines.append(f"puts $TARGET_LIBRARY_FILES_STA\n")
    lines.append(f"\n")
    lines.append(
        f"# Extra link logical libraries not included in TARGET_LIBRARY_FILES\n"
    )
    lines.append(f"# Here specify all *.db you want to use\n")
    lines.append(f"# Topological mode uses MW libs w/o bc corner *.db\n")
    lines.append(f'set ADDITIONAL_LINK_LIB_FILES ""\n')
    lines.append(f"\n")

    max_name = f""
    min_name = f""

    for mode in modes:
        if mode["corner"] == "wc1":
            max_name = f'TS_NLDM_DB_{mode["name"].upper()}_VIEWS'
        elif mode["corner"].startswith("wc"):
            max_name = f'TS_NLDM_DB_{mode["name"].upper()}_VIEWS'
        if mode["corner"] in "bc":
            min_name = f'TS_NLDM_DB_{mode["name"].upper()}_VIEWS'

    lines.append(
        f'# List of max min library pairs "max1 min1 max2 min2 max3 min3" ... \n'
    )
    lines.append(f' set MIN_LIBRARY_FILES ""\n')
    lines.append(f"foreach min ${min_name} max ${max_name} {{\n")
    lines.append(f" lappend MIN_LIBRARY_FILES $max $min\n")
    lines.append(f"}}\n")

    lines.append(f"\n")

    if "wireload" in TsGlobals.TS_DESIGN_CFG["design"]:
        lines.append(
            f"##########################################################################################\n"
        )
        lines.append(f"# Wireload\n")
        lines.append(
            f"##########################################################################################\n"
        )
        lines.append(
            f"set wireload       [dict get $TS_{str(ts_get_design_top())}_WIRELOAD]\n"
        )
        lines.append(f"\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"# Milkyway\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    lines.append(f"# Tcl file with library modifications for dont_use\n")
    lines.append(f'set LIBRARY_DONT_USE_FILE ""\n')
    lines.append(f"\n")
    lines.append(f"# Tcl file for customized dont use list before first compile\n")
    lines.append(f'set LIBRARY_DONT_USE_PRE_COMPILE_LIST ""\n')
    lines.append(f"\n")
    lines.append(
        f"# Tcl file with library modifications for dont_use before incr compile\n"
    )
    lines.append(f'set LIBRARY_DONT_USE_PRE_INCR_COMPILE_LIST ""\n')
    lines.append(f"\n")
    lines.append(f"# Dont touch ts_common_blocks\n")
    lines.append(f"set DONT_TOUCH_TS_COMMON_BLOCKS true\n")
    lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f"set MW_REFERENCE_LIB_DIRS $TS_MILKYWAY_VIEW_DIRS\n")
    lines.append(f"\n")
    lines.append(f'set NDM_REFERENCE_LIB_DIRS ""\n')
    lines.append(f"\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"# Input file names/paths\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    lines.append(f"# Netlist file\n")
    lines.append(f"set NETLIST_FILES {TsGlobals.TS_STA_DC_RM_NETLIST}\n")
    lines.append(f"\n")
    lines.append(f"# Constaints as an TCL, not SDC standard\n")
    lines.append(
        f"set DCRM_CONSTRAINTS_INPUT_FILE [set TS_{str(ts_get_design_top())}_[set MODE]_CONSTRAINTS] \n"
    )
    lines.append(f"\n")
    lines.append(f"# Constaints SDC standard\n")
    lines.append(f'set DCRM_SDC_INPUT_FILE ""\n')
    lines.append(f"\n")
    lines.append(
        f"# This variable points to where DC builds its internal design representation\n"
    )
    lines.append(f"set TS_STA_DIR {TsGlobals.TS_STA_RUN_DIR}/build\n")
    lines.append(f"\n")
    if args.sign_off:
        lines.append(
            f"##########################################################################################\n"
        )
        lines.append(f"# Back Annotation File Section\n")
        lines.append(
            f"##########################################################################################\n"
        )
        lines.append(f"\n")
        lines.append(f"# Parasitic files\n")
        lines.append(f"set PARASITIC_FILES [dict get $MODES $MODE spef]\n")
        lines.append(f"\n")
        lines.append(
            f'set PARASITIC_PATHS {ts_get_root_rel_path(TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"][args.source_data])}/{TsGlobals.TS_STA_RUNCODE}/results/ \n'
        )
        lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f'puts "RM-Info: Completed script [info script]"\n')
    lines.append(f"\n")

    # Create and write
    with open(path, "w") as setup_file:
        setup_file.writelines(lines)


def sta_open_design(args):
    """
    Generates pt_shell run file for re-opening sta database
    Opens only local data
    Includes autochecked for dmsa vs single mode opening
    : param args: arguments
    """
    # Empty buffer - generation to be line by line
    lines = []
    # Content of a file
    lines.append(f"\n")
    if args.mode is not None:
        for i, mode in enumerate(TsGlobals.TS_DESIGN_CFG["design"]["modes"]):
            if args.mode in mode["name"]:
                lines.append(
                    f'restore_session ./{mode["name"]}_{mode["corner"]}/{str(ts_get_design_top()).lower()}_ss \n'
                )
    else:
        lines.append(f"restore_session ./{str(ts_get_design_top()).lower()}_ss \n")
    lines.append(f"\n")

    # Create and write
    with open(TsGlobals.TS_STA_DC_RM_OPENFILE, "w") as run_file:
        run_file.writelines(lines)


def __sta_netlist_selection(args):
    """
    Search a netlist according to default settings from --sourdce <flow_dir>
    or try to identify a netlist --netlist <file> [absolute or relative path]
    """
    if args.netlist:
        # Here we use customer entered netlist
        path = f"{ts_get_root_rel_path(args.netlist)}"
    else:
        # Use default netlist location from flow_dirs/results/<design_name>.v
        path = f'{ts_get_root_rel_path(TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"][args.source_data])}/{TsGlobals.TS_STA_RUNCODE}/results/{str(ts_get_design_top()).lower()}.v'

    if os.path.isfile(path):
        return path
    else:
        ts_throw_error(TsErrCode.ERR_STA_4, path)
        return None


def sta_release(source_dir, release_dir, flow_dir_type):
    """
    Hard-copy data from source directory to release directory
    """
    if source_dir is not release_dir:
        os.makedirs(release_dir, exist_ok=True)
        shutil.copytree(
            eval(f"TsGlobals.TS_{str(flow_dir_type).upper()}_REPORTS_DIR"),
            f"{release_dir}/reports",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            eval(f"TsGlobals.TS_{str(flow_dir_type).upper()}_LOGS_DIR"),
            f"{release_dir}/logs",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            eval(f"TsGlobals.TS_{str(flow_dir_type).upper()}_RESULTS_DIR"),
            f"{release_dir}/results",
            dirs_exist_ok=True,
        )
        ts_print("Release is done!", color=TsColors.PURPLE, big=True)
