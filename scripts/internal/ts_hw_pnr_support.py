# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square
# Functions for ts_pnr_run.py
#
# TODO: License
####################################################################################################


import logging
import os
import shutil
import subprocess
from datetime import datetime

from .ts_hw_cfg_parser import parse_runcode_arg
from .ts_hw_common import (
    get_env_var_path,
    get_repo_root_path,
    ts_get_design_top,
    ts_set_env_var,
)
from .ts_hw_design_config_file import check_export_view_types
from .ts_hw_export import export_dc_tcl, export_design_config
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsColors,
    TSFormatter,
    TsInfoCode,
    ts_debug,
    ts_info,
    ts_print,
)


def set_pnr_global_vars(args):
    """
    Set pnr flow python TsGlobals variables
    """
    # Check runcode validity and update it if the _n+1 rule is applicable
    TsGlobals.TS_PNR_RUNCODE = parse_runcode_arg(args)
    # Set PNR run dir according to runcode
    TsGlobals.TS_PNR_RUN_DIR = get_pnr_rundir(TsGlobals.TS_PNR_RUNCODE)
    # Set PNR dirs for purpose of the run
    TsGlobals.TS_PNR_LOGS_DIR = os.path.join(
        TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_LOGS_DIR
    )
    TsGlobals.TS_PNR_RESULTS_DIR = os.path.join(
        TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_RESULTS_DIR
    )
    TsGlobals.TS_PNR_REPORTS_DIR = os.path.join(
        TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_REPORTS_DIR
    )
    # Setting paths for opening PnR database
    TsGlobals.TS_PNR_OPENFILE = os.path.join(
        TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_OPENFILE
    )
    # Setting design_cfg file path and name
    TsGlobals.TS_PNR_DESIGN_CFG_FILE = os.path.join(
        TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_DESIGN_CFG_FILE
    )
    # Setting mcmm setup file path and name
    TsGlobals.TS_PNR_MCMM_FILE = os.path.join(
        TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_MCMM_FILE
    )


def create_pnr_sub_dirs():
    """
    Create directory in "pnr" folder.
    :param name: Name of the sub-directory within TS_REPO_ROOT/pnr/{name} directory to be created.

    """
    # Main runcode subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_PNR_RUN_DIR)
    os.makedirs(TsGlobals.TS_PNR_RUN_DIR, exist_ok=True)
    # Logs subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_PNR_LOGS_DIR)
    os.makedirs(TsGlobals.TS_PNR_LOGS_DIR, exist_ok=True)
    # Results subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_PNR_RESULTS_DIR)
    os.makedirs(TsGlobals.TS_PNR_RESULTS_DIR, exist_ok=True)
    # Report subdir
    ts_info(TsInfoCode.INFO_SYS_4, TsGlobals.TS_PNR_REPORTS_DIR)
    os.makedirs(TsGlobals.TS_PNR_REPORTS_DIR, exist_ok=True)


def delete_pnr_sub_dir():
    """
    Delete directiory in "pnr" folder
    : param name: Name of the sub-directory within TS_REPO_ROOT/pnr/{name} to be deleted

    """
    ts_info(TsInfoCode.INFO_SYS_5, TsGlobals.TS_PNR_RUN_DIR)
    shutil.rmtree(TsGlobals.TS_SYN_RUN_DIR, ignore_errors=True)


def get_pnr_rundir(runcode: str):
    """
    Returns full path of pnr directory
    """
    return f"{get_repo_root_path()}/pnr/{runcode}"


def open_result_test(args):
    """
    Returns True or False of runcode directory existance test
    """
    path = f"{get_repo_root_path()}/pnr/{args.runcode}"
    ts_debug(f"Testing folder {path}")
    return os.path.isdir(path)


def build_icc2_cmd(args):
    """
    Builds command for icc2_shell
    """

    # GIT SHA CMD
    # git_cmd = f"`git log --pretty=format:'%H' -n 1`"

    # List of all variables used for place and route flow that is passed as a single icc2_shell command
    # pnr_cfg_args += f'-x \\"set RUNCOCE {TsGlobals.TS_PNR_RUNCODE};'
    # pnr_cfg_args += f'set GIT_COMMIT_SHA {git_cmd};cd {TsGlobals.TS_PNR_RUN_DIR}\\"'

    pnr_flow_dict = {
        "init_design": f"icc2_shell -f ./rm_icc2_pnr_scripts/init_design.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/init_design.log;",
        "place_opt": f"icc2_shell -f ./rm_icc2_pnr_scripts/place_opt.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/place_opt.log;",
        "clock_opt": f"icc2_shell -f ./rm_icc2_pnr_scripts/clock_opt_cts.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/clock_opt_cts.log;",
        "clock_opt_opto": f"icc2_shell -f ./rm_icc2_pnr_scripts/clock_opt_opto.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/clock_opt_opto.log;",
        "route_auto": f"icc2_shell -f ./rm_icc2_pnr_scripts/route_auto.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/route_auto.log;",
        "route_opt": f"icc2_shell -f ./rm_icc2_pnr_scripts/route_opt.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/route_opt.log;",
        "chip_finish": f"icc2_shell -f ./rm_icc2_pnr_scripts/chip_finish.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/chip_finish.log;",
        "icv_in_design": f"icc2_shell -f ./rm_icc2_pnr_scripts/icv_in_design.tcl | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/icv_in_design.log;",
    }

    pnr_flow = ""

    # Select between either opening of design or running new PnR
    if args.open_result:
        # Open a given step
        time = "{}".format(datetime.now().strftime("_%Y_%m_%d_%H_%M_%S_%f"))
        pnr_flow += f"icc2_shell -f {TsGlobals.TS_PNR_OPENFILE} | tee -i {TsGlobals.TS_PNR_LOGS_DIR}/open_design_{time}.log;"
    else:
        # Prepare batch cmd
        for key in pnr_flow_dict:
            pnr_flow += pnr_flow_dict.get(key)
            if key == args.pnr_target:
                break

    # Final icc2_shell command completition
    pnr_cmd = f'TERM=xterm /usr/bin/bash -c "{pnr_flow}"'

    # Report final dc_cmd
    ts_info(TsInfoCode.INFO_SYS_3, "icc2_shell", pnr_cmd)

    return pnr_cmd


def pnr_logging(args):
    """
    Configures additional handler for logging pnr flow file log
    :args: Argparse command line arguments object.
    """

    # Get existing logger
    logger = logging.getLogger()
    # Create time stamp for a log file name
    date_time = datetime.now()
    # Set full path and a name of the log file
    os.makedirs(TsGlobals.TS_PNR_LOGS_DIR, exist_ok=True)
    filename = f'{TsGlobals.TS_PNR_LOGS_DIR}/{date_time.strftime("%y%m%d.%H%M%S")}.log'
    handler = logging.FileHandler(filename)
    handler.setFormatter(TSFormatter(use_colors=False))
    logger.addHandler(handler)


def set_license_queuing(args, tool_type, env_var):
    """
    Enables/Disables license queuing for synopsys tools
    :param args
    :param tool_type: name/type of tool
    :param env_var: enviromental variable to be set
    """
    # If not set, do not define the variable. The False value is not working. It is synopsys tools bug.
    if args.license_wait:
        ts_info(TsInfoCode.GENERIC, f"Enabling {tool_type} license queuing.")
        ts_set_env_var(f"{env_var}", "True")


def set_license_wait_time(args, tool_type, env_var, time):
    """
    Setting of maximum wait time for a licence
    :param args
    :param tool_type: name/type of tool
    :param env_var: enviromental variable to be set
    :param time: time in seconds
    """
    # If not set, do not define the variable. The False value is not working. It is synopsys tools bug.
    if args.license_wait:
        ts_info(
            TsInfoCode.GENERIC,
            f"Maximum waiting time {time} for {tool_type} license queuing.",
        )
        ts_set_env_var(f"{env_var}", time)


def pnr_design_cfg_file(args):
    """
    Generates design configuration TCL script
    * Executes selected procedures from ts_design_cfg script
    * Generated file to be stored in TS_PNR_RUN_DIR directory
    """
    # adds argumens used with check_export_view_types and export_design_config procedures
    views_to_add = "nldm_db,ccs_db,lef,milkyway"
    setattr(args, "add_views", views_to_add)

    setattr(
        args,
        "add_top_entity",
        TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_DESIGN_CFG["design"]["target"]][
            "top_entity"
        ],
    )
    setattr(args, "add_syn_rtl_build_dirs", False)
    setattr(args, "add_constraints", True)

    add_topo_data = True

    setattr(args, "add_floorplan", add_topo_data)
    setattr(args, "add_tluplus", add_topo_data)
    setattr(args, "add_map_tech", add_topo_data)

    setattr(args, "add_spef", False)
    setattr(args, "add_wireload", True)
    setattr(args, "add_opcond", True)

    TsGlobals.TS_EXP_VIEWS = args.add_views.split(",")

    # ts_hw_design_config_file used in ts_design_cfg.py
    check_export_view_types(args)

    # ts_hw_design_config_file used in ts_design_cfg.py
    export_design_config(TsGlobals.TS_PNR_DESIGN_CFG_FILE, args)


def pnr_mcmm_file(path: str, args):
    """
    Generates RM_MCMM_SCENARIOS_SETUP_FILE - bridge file between pdk cfg, design cfg, sim cfg and synthesis flow to support mcmm methodology
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
    lines.append(f"# Multi-mode multi-corner file\n")
    lines.append(f"# Script: {TsGlobals.TS_PNR_MCMM_FILE}\n")
    lines.append(f"# Version: R-2021.04-SP3\n")
    lines.append(f"# Copyright (C) Tropic Square. All rights reserved.\n")
    lines.append(
        f"##########################################################################################\n"
    )

    # Create list of modes
    if modes is not None:
        lines.append(f"set scenarios [dict create]\n\n")

    # What we call modes is considered scenarious with PnR tools
    for mode in modes:
        lines.append(f"dict set scenarios {mode['name'].upper()} {{ \n")

        for key in mode:
            lines.append(f" {key} {mode[key]} \n")

        lines.append(f"}}\n\n")
    lines.append(f"\n")
    lines.append(f"remove_scenario -all; remove_modes -all; remove_corners -all\n")
    lines.append(f"\n")
    lines.append(f"# Create modes, corners, scenarious\n")
    lines.append(f"\n")
    lines.append(f"foreach scenario [dict keys $scenarious] {{\n")
    lines.append(f"     create_corner [dict get $scenarious $scenario corner]\n")
    lines.append(f"     create_mode [dict get $scenarious $scenario name]\n")
    lines.append(f"     create_scenario [dict get $scenarious $scenario name]\n")
    lines.append(
        f"     set_scenario_options -dynamic_power true -leakage_power true -setup true -hold false\n"
    )
    lines.append(f"}}\n")
    lines.append(f"\n")
    lines.append(f"# Populate constraints and parasitic parameters\n")
    lines.append(f"foreach scenario [dict keys $scenarious] {{\n")
    lines.append(f"     current_scenario $scenario\n")
    lines.append(f'     puts "RM-info: current scenario $scenario"\n')
    lines.append(
        f"     set file_name [file tail [file rootname [dict get $scenarious $scenario tluplus]] \n"
    )
    lines.append(
        f"     read_parasitic_tech -tlup [dict get $scenarious $scenario tluplus] -layermap $TS_{str(ts_get_design_top())}_MAP -name $file_name \n"
    )
    lines.append(f"     rm_source -file [dict get $scenarious $scenario constraints]\n")
    lines.append(f"}}\n")
    lines.append(f"\n")
    lines.append(f"unset scenarious\n")

    # Create and write
    with open(path, "w") as setup_file:
        setup_file.writelines(lines)


def pnr_setup(path: str, args):
    """
    Generates ts_pnr_setup file - bridge between pdk cfg, design cfg, sim cfg and pnr flow
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
    lines.append(f"# Variables common to all reference methodology scriptsn\n")
    lines.append(f"# Script: {TsGlobals.TS_PNR_SETUP_FILE}\n")
    lines.append(f"# Version: R-2021.04-SP3\n")
    lines.append(f"# Copyright (C) Tropic Square. All rights reserved.\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    # Entry point for usage auto-generated design.tcl
    lines.append(f"source -echo -verbose {TsGlobals.TS_PNR_DESIGN_CFG_FILE}\n")
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

        for key in mode:
            lines.append(f" {key} {mode[key]} \n")

        lines.append(f"}}\n\n")

    lines.append(f"\n")
    lines.append(
        f"set ADDITIONAL_SEARCH_PATH [concat ${{TS_NLDM_DB_VIEW_DIRS}} ${{TS_CCS_DB_VIEW_DIRS}} ${{TS_{str(ts_get_design_top())}_RTL_SYN_BUILD_DIRS}}] \n"
    )
    lines.append(f"\n")
    lines.append(f"\n")
    lines.append(f"# Target library\n")
    lines.append(f'set TARGET_LIBRARY_FILES ""\n')
    lines.append(f"\n")
    lines.append(f"foreach MODE [dict keys $MODES] {{\n")
    lines.append(
        f" set TARGET_LIBRARY_FILES [concat [set TARGET_LIBRARY_FILES] [set TS_NLDM_DB_[set MODE]_VIEWS]] \n"
    )
    lines.append(f"}}\n")
    lines.append(f"\n")
    lines.append(f"puts $TARGET_LIBRARY_FILES\n")
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
        if mode["corner"] in "wc":
            max_name = f'TS_NLDM_DB_{mode["name"].upper()}_VIEWS'
        if mode["corner"] in "bc":
            min_name = f'TS_NLDM_DB_{mode["name"].upper()}_VIEWS'

    lines.append(
        f'# List of max min library pairs "max1 min1 max2 min2 max3 min3" ... \n'
    )
    lines.append(f' set MIN_LIBRARY_FILES ""\n')
    lines.append(f"foreach min ${min_name} max ${max_name} {{\n")
    lines.append(f" lappend MIN_LIBRARY_FILES $min $max\n")
    lines.append(f"}}\n")

    lines.append(f"\n")
    lines.append(f"set OPCOND ${{TS_{str(ts_get_design_top())}_OPCOND}}  \n")
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
    lines.append(
        f"# TODO: Remove indirect pass and pass TS_MILKYWAY_DIRS to main pnr script.\n"
    )
    lines.append(f"if {{ $DC_TOPO }} {{\n")
    lines.append(f"    set MW_REFERENCE_LIB_DIRS $TS_MILKYWAY_VIEW_DIRS\n")
    lines.append(f"}}\n")
    lines.append(f"\n")
    lines.append(f'set NDM_REFERENCE_LIB_DIRS ""\n')
    lines.append(f"\n")
    if "tech" in TsGlobals.TS_DESIGN_CFG["design"]:
        lines.append(f"set MW_TECH_FILE $TS_{str(ts_get_design_top())}_TECH\n")
        lines.append(f"\n")
    if "map" in TsGlobals.TS_DESIGN_CFG["design"]:
        lines.append(f"set MW_MAP_FILE $TS_{str(ts_get_design_top())}_MAP\n")
        lines.append(f"\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"# Input file names/paths\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    lines.append(
        f"# Script which is generated by ts_sim_compile.py which analyses RTL.\n"
    )
    lines.append(
        f"#set DCRM_RTL_READ_SCRIPT {TsGlobals.TS_PNR_RUN_DIR}/{TsGlobals.TS_SYN_SRC_RTL_FILE}\n"
    )
    lines.append(f"\n")
    lines.append(f"# Constaints as an TCL, not SDC standard\n")
    lines.append(
        f'set DCRM_CONSTRAINTS_INPUT_FILE "$TS_{str(ts_get_design_top())}_GLOBAL_CONSTRAINTS"\n'
    )
    lines.append(f"\n")
    lines.append(f"# Constaints SDC standard\n")
    lines.append(f'set DCRM_SDC_INPUT_FILE ""\n')
    lines.append(f"\n")
    lines.append(
        f"# This variable points to where DC builds its internal design representation\n"
    )
    lines.append(f"set TS_PNR_DIR {TsGlobals.TS_PNR_RUN_DIR}/build\n")
    lines.append(f"\n")
    if "floorplan" in TsGlobals.TS_DESIGN_CFG["design"]:
        lines.append(f"# Floorplan file\n")
        lines.append(
            f"set DCRM_DCT_DEF_INPUT_FILE $TS_{str(ts_get_design_top())}_FLOORPLAN\n"
        )
        lines.append(f"\n")
    lines.append(f"# Set variable for multi-corner multi-mode script path\n")
    lines.append(f"set DCRM_MCMM_SCENARIOS_SETUP_FILE {TsGlobals.TS_PNR_MCMM_FILE}\n")
    lines.append(f"\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"# Flow configuration\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    lines.append(f"# Set variable OPTIMIZATION_FLOW from following RM+ flows\n")
    lines.append(f"# High Performance Low Power (hplp)\n")
    lines.append(f"# High Connectivity (hc)\n")
    lines.append(f"# Runtime Exploration (rtm_exp)\n")
    lines.append(f"\n")
    lines.append(f"# Specify one flow output of hllp | hc | rtm_exp | tim\n")
    lines.append(f'set OPTIMIZATION_FLOW "tim" \n')
    lines.append(f"\n")
    lines.append(
        f"# Use reduced effort for lower runtime in hplp and time flows (false | true)\n"
    )
    lines.append(f'set REDUCES_EFFORT_OPTIMIZATION_FLOW "true "\n')
    lines.append(f"\n")
    lines.append(
        f"suppress_message UCN-1; # This is OK to suppress, only warning if multiple ports are connected to the same wire, no problem.\n"
    )
    lines.append(
        f"suppress_message TIM-164; # We cannot ensure all libraries to be characterized for common thresholds\n"
    )
    lines.append(f"suppress_message TIM-175; # \n")
    lines.append(f"\n")
    lines.append(f"unset MODES\n")
    lines.append(f'puts "RM-Info: Completed script [info script]"\n')
    lines.append(f"\n")

    # Create and write
    with open(path, "w") as setup_file:
        setup_file.writelines(lines)


def __pnr_netlist_selection(args):
    """
    Search a netlist according to default settings from --source <flow_dir>
    or try to identify a netlist --netlist <file> [absolute or relative path]
    """
    if args.netlist:
        # Here we use customer entered netlist
        path = f"{ts_get_root_rel_path(args.netlist)}"
    else:
        # Use default netlist location from flow_dirs/results/<design_name>.v
        path = f'{ts_get_root_rel_path(TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"][args.source_data])}/{TsGlobals.TS_PNR_RUNCODE}/results/{str(ts_get_design_top()).lower()}.v'

    if os.path.isfile(path):
        return path
    else:
        ts_throw_error(TsErrCode.ERR_PNR_4, path)
        return None


def pnr_open_design(args):
    """
    Generates icc2 run file for re-opening PnR database
    : param args: arguments
    """
    # Empty buffer - generation to be line by line
    lines = []

    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"# Script: {TsGlobals.TS_PNR_OPENFILE}.tcl for ICC2 PnR tool\n")
    lines.append(
        f"##########################################################################################\n"
    )
    lines.append(f"\n")
    lines.append(f"source ./rm_utilities/procs_global.tcl\n")
    lines.append(f"source ./rm_utilities/procs_icc2.tcl\n")
    lines.append(f"rm_source -file ./rm_setup/design_setup.tcl\n")
    lines.append(f"rm_source -file ./rm_setup/icc2_pnr_setup.tcl\n")
    lines.append(f"rm_source -file ./rm_setup/header_icc2_pnr.tcl\n")
    lines.append(
        f"rm_source -file sidefile_setup.tcl -after_file technology_override.tcl\n"
    )
    lines.append(f"\n")
    lines.append(f"set CURRENT_STEP  {args.pnr_target}_open\n")
    lines.append(f"set PREVIOUS_STEP {args.pnr_target}\n")
    lines.append(f"puts RM-info: CURRENT_STEP  = $CURRENT_STEP \n")
    lines.append(f"\n")
    lines.append(
        f'rm_source -file $TCL_PVT_CONFIGURATION_FILE -optional -print "TCL_PVT_CONFIGURATION_FILE"\n'
    )
    lines.append(f"open_lib $DESIGN_LIBRARY\n")
    lines.append(
        f"copy_block -from ${{DESIGN_NAME}}/${{PREVIOUS_STEP}} -to ${{DESIGN_NAME}}/${{CURRENT_STEP}}\n"
    )
    lines.append(f"current_block ${{DESIGN_NAME}}/${{CURRENT_STEP}}\n")
    lines.append(f"\n")
    lines.append(f'if {{$SET_QOR_STRATEGY_MODE == "early_design"}} {{}} \n')
    lines.append(f" set_early_data_check_policy -policy lenient -if_not_exist\n")
    lines.append(f'elseif {{ $EARLY_DATA_CHECK_POLICY != "none"  }} \n')
    lines.append(
        f" set_early_data_check_policy -policy $EARLY_DATA_CHECK_POLICY -if_not_exist\n"
    )
    lines.append(f"}}\n")
    lines.append(f"\n")
    lines.append(f"link_block\n")
    lines.append(f"\n")

    # Create and write
    with open(TsGlobals.TS_PNR_OPENFILE, "w") as run_file:
        run_file.writelines(lines)


def release(source_dir, release_dir, flow_dir_type):
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
        ts_print("Release is done!", TsColors.PURPLE, big=True)
