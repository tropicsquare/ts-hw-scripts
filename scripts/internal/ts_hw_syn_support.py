#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square
# Functions for ts_syn_run.py

#
# TODO: License
####################################################################################################


import os
from datetime import datetime
import sys
import select
import termios
import tty
import pty

from internal import *
from .ts_hw_common import *
from .ts_hw_source_list_files import *
from .ts_grammar import *


def exec_cmd_in_dir_interactive(directory: str, command: str ) -> int:
    """
    Executes a command in a directory in pseudo-terminal interactively.
    :param directory: Directory in which command shall be executed
    :param command: Command to execute.
    """

    # Save original tty setting then set it to raw mode
    old_tty = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())
    
    # open pseudo-terminal to interact with subprocess
    master_fd, slave_fd = pty.openpty()

    try:
        # Launch the command
        p = subprocess.Popen(command,
                         preexec_fn=os.setsid,
                         stdin=slave_fd,
                         stdout=slave_fd,
                         stderr=slave_fd,
                         shell=True,
                         cwd=directory,
                         universal_newlines=True)

        while p.poll() is None:
            # Time-out is extremely important otherwise finished XTERM hangs
            # and keyboard input is needed to exit subprocess
            r,w,e = select.select([sys.stdin,master_fd],[],[],0.01)
            if sys.stdin in r:
                d = os.read(sys.stdin.fileno(),10240)
                os.write(master_fd,d)
            elif master_fd in r:
                o = os.read(master_fd,10240)
                if o:
                    os.write(sys.stdout.fileno(),o)
    finally:
        # restore tty settings back
        termios.tcsetattr(sys.stdin,termios.TCSADRAIN,old_tty)

    return p.wait()

def set_syn_global_vars(args):
    """
    Set synthesis flow global variables 
    """
    # Set synthesis run dir according to runcode
    TsGlobals.TS_SYN_RUN_DIR = get_syn_rundir(args)
    # Set sythesis dirs for purpose of the run
    TsGlobals.TS_SYN_LOGS_DIR = join(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_LOGS_DIR)
    TsGlobals.TS_SYN_RESULTS_DIR = join(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_RESULTS_DIR)
    TsGlobals.TS_SYN_REPORTS_DIR = join(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_REPORTS_DIR)
    # Setting paths for open synthesis database
    TsGlobals.TS_SYN_DC_RM_OPENFILE = join(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_DC_RM_OPENFILE)
    # Setting path for run sythesis
    TsGlobals.TS_SYN_DC_RM_RUNFILE =  join(get_env_var_path(TsGlobals.TS_SYN_FLOW_PATH),TsGlobals.TS_SYN_DC_RM_RUNFILE)
    # Setting synthesis build dir for rtl sub-blocks compilation
    TsGlobals.TS_SYN_BUILD_DIR = join(TsGlobals.TS_SYN_RUN_DIR,"build")
    # Setting design_cfg file path and name
    TsGlobals.TS_SYN_DESIGN_CFG_FILE = join(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_DESIGN_CFG_FILE)


def create_syn_sub_dirs():
    """
    Create directory in "syn" folder.
    :param name: Name of the sub-directory within TS_REPO_ROOT/syn/{name} directory to be created.

    """
    # Main runcode subdir
    ts_info(TsInfoCode.INFO_SYS_4,TsGlobals.TS_SYN_RUN_DIR)
    os.makedirs(TsGlobals.TS_SYN_RUN_DIR, exist_ok=True)
    # Logs subdir
    ts_info(TsInfoCode.INFO_SYS_4,TsGlobals.TS_SYN_LOGS_DIR)
    os.makedirs(TsGlobals.TS_SYN_LOGS_DIR, exist_ok=True)
    # Results subdir
    ts_info(TsInfoCode.INFO_SYS_4,TsGlobals.TS_SYN_RESULTS_DIR)
    os.makedirs(TsGlobals.TS_SYN_RESULTS_DIR, exist_ok=True)
    # Report subdir
    ts_info(TsInfoCode.INFO_SYS_4,TsGlobals.TS_SYN_REPORTS_DIR)
    os.makedirs(TsGlobals.TS_SYN_REPORTS_DIR, exist_ok=True)


def delete_syn_sub_dir():
    """
    Delete directiory in "syn" folder
    : param name: Name of the sub-directory within TS_REPO_ROOT/syn/{name} to be deleted

    """
    ts_info(TsInfoCode.INFO_SYS_5,TsGlobals.TS_SYN_RUN_DIR)
    shutil.rmtree(TsGlobals.TS_SYN_RUN_DIR, ignore_errors=True)


def get_syn_rundir(args):
    """
    Returns full path of synthesis directory
    """
    return f'{get_repo_root_path()}/syn/{args.runcode}'


def open_result_test(args):
    """
    Returns True or False of runcode directory existance test
    """
    path = f'{get_repo_root_path()}/syn/{args.runcode}'
    return os.path.isdir(path)


def build_synthesis_cmd(args):
    """
    Builds command for dc_shell
    """

    # Fixed structure of DC synthesis flow
    # TOPO MODE
    if args.topo:
        dc_cfg_args = f'-topo '
    else:
        dc_cfg_args = f''

    # Select between either opening of design or running new sythesis
    if args.open_result:
        # Path to DC_RM_OPENFILE
        dc_cfg_args += f'-f {TsGlobals.TS_SYN_DC_RM_OPENFILE} '
    else:
        # Path DC_RM_RUNFILE
        dc_cfg_args += f'-f {TsGlobals.TS_SYN_DC_RM_RUNFILE} '


    # LOG FILE
    logfile = f'{TsGlobals.TS_SYN_LOGS_DIR}/{args.runcode}_syn.log'
    dc_cfg_args += f'-output {logfile} '

    # GIT SHA CMD
    git_cmd = f'`git log --pretty=format:\'%H\' -n 1`'

    # List of all variables used for synthesis flow that is passed as a single dc_shell command
    dc_cfg_args += f'-x \\"set REPORT_POSTPROC {args.report_postproc};set DC_TOPO {args.topo};' 
    dc_cfg_args += f'set QUICK {args.quick_run};set NOFLOORPLAN {args.no_floorplan};set RUNCODE_CMD_LINE {args.runcode};'
    dc_cfg_args += f'set RESULTS_DIR {TsGlobals.TS_SYN_RESULTS_DIR};set REPORTS_DIR {TsGlobals.TS_SYN_REPORTS_DIR};'
    dc_cfg_args += f'set GIT_COMMIT_SHA {git_cmd};cd {TsGlobals.TS_SYN_RUN_DIR}\\"'

    # Final dc_shell command completition
    dc_cmd = f'TERM=xterm /usr/bin/bash -c "dc_shell -64 {dc_cfg_args}" '
    
    # Report final dc_cmd
    ts_info(TsInfoCode.INFO_SYS_3,"dc_shell",dc_cmd)
    
    return dc_cmd


def syn_logging(args):
    """
    Configures additional handler for logging synthesis flow file log
    :args: Argparse command line arguments object.
    """
    
    # Get existing logger
    logger = logging.getLogger()
    # Create time stamp for a log file name
    date_time = datetime.now()
    # Set full path and a name of the log file
    filename = f'{get_repo_root_path()}/syn/logs/{args.runcode}_{date_time.strftime("%y%m%d.%H%M%S")}.log'
    handler = logging.FileHandler(filename)
    handler.setFormatter(TSFormatter(use_colors=False))
    logger.addHandler(handler)


def set_license_queuing(args,tool_type,env_var):
    """
    Enables/Disables license queuing for synopsys tools
    :param args
    :param tool_type: name/type of tool
    :param env_var: enviromental variable to be set
    """
    # If not set, do not define the variable. The False value is not working. It is synopsys tools bug.
    if args.license_wait:
        ts_info(TsInfoCode.GENERIC, f'Enabling {tool_type} license queuing.')
        ts_set_env_var(f'{env_var}', "True")


def syn_rtl_src_file(args):
    """
    Generates target RTL synthesis TCL script
    * Executes the ts_sim_compile.load_source_list_files that prepared data for export
    * This assumes that you have RTL target (--exp-tcl-file-dc) defined in your *IP/sim/ts_sim_cfg.yml as ts_sim_config.yml
    * Synthesis flow uses DCRM_RTL_READ_SCRIPT variable name

    """
    # Export source list regarding target to dc_shell_rtl_src file - ts_hw_export
    export_dc_tcl(f'{TsGlobals.TS_SYN_RUN_DIR}/{TsGlobals.TS_SYN_SRC_RTL_FILE}')

def syn_design_cfg_file(args):
    """
    Generates design configuration TCL script
    * Executes selected procedures from ts_design_cfg script 
    * Generated file to be stored in TS_SYN_RUN_DIR directory
    """
    # adds argumens used with check_export_view_types and export_design_config procedures
    setattr(args,"add_views","nldm_db,ccs_db,lef,milkyway")
    setattr(args,"add_top_entity",TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_DESIGN_CFG["design"]["target"]]["top_entity"])
    setattr(args,"add_syn_rtl_build_dirs",True)
    setattr(args,"add_constraints",True)
    setattr(args,"add_floorplan",True)
    setattr(args,"add_spef",False)

    TsGlobals.TS_EXP_VIEWS = args.add_views.split(",")
    # ts_hw_design_config_file used in ts_design_cfg.py
    check_export_view_types(args)
    # ts_hw_design_config_file used in ts_design_cfg.py
    export_design_config(TsGlobals.TS_SYN_DESIGN_CFG_FILE, args)



def syn_setup(path: str, args):
    """
    Generates ts_synthesis_setup file - bridge between pdk cfg, design cfg, sim cfg and synthesis flow
    : param path: path where to generate the file + name of the file
    : param args: arguments
    """

    # Modes
    modes = TsGlobals.TS_DESIGN_CFG['design']['modes']

    # Empty buffer - generation to be line by line
    lines = []

    lines.append(f'##########################################################################################\n')
    lines.append(f'# Variables common to all reference methodology scriptsn\n')
    lines.append(f'# Script: {TsGlobals.TS_SYN_SETUP_FILE}\n')
    lines.append(f'# Version: R-2021.04-SP3\n')
    lines.append(f'# Copyright (C) Tropic Square. All rights reserved.\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'\n')
    # Entry point for usage auto-generated design.tcl
    lines.append(f'source -echo -verbose {TsGlobals.TS_SYN_DESIGN_CFG_FILE}\n')
    lines.append(f'# The name of top level design\n')
    lines.append(f'set DESIGN_NAME \"{str(ts_get_design_top()).lower()}\"\n')
    lines.append(f'\n')
    lines.append("##########################################################################################\n")
    lines.append("# Library Setup Variables\n")
    lines.append(f'\n')
    lines.append(f'set ADDITIONAL_SEARCH_PATH [list ${{TS_NLDM_DB_VIEW_DIRS}} ${{TS_CCS_DB_VIEW_DIRS}} ${{TS_TASSIC_TOP_RTL_SYN_BUILD_DIRS}}] \n')
    lines.append(f'\n')
    lines.append(f'\n')
    lines.append(f'# Target library\n')
    lines.append(f'set TARGET_LIBRARY_FILES ${{TS_NLDM_DB_FUNC_MAX_VIEWS}}\n')
    lines.append(f'\n')
    lines.append(f'\n')
    lines.append(f'# Extra link logical libraries not included in TARGET_LIBRARY_FILES\n')
    lines.append(f'# Here specify all *.db you want to use\n')
    lines.append(f'# Topological mode uses MW libs w/o bc corner *.db\n')
    lines.append(f'set ADDITIONAL_LINK_LIB_FILES ""\n')
    lines.append(f'\n')
    lines.append(f'# List of max min library pairs "max1 min1 max2 min2 max3 min3" ... \n')
    lines.append(f' set MIN_LIBRARY_FILES ""\n')
    lines.append(f'foreach min ${{TS_NLDM_DB_FUNC_MAX_VIEWS}} max ${{TS_NLDM_DB_FUNC_MIN_VIEWS}} {{\n')
    lines.append(f' lappend MIN_LIBRARY_FILES $min $max\n')
    lines.append(f'}}\n')
    #lines.append(f'{modes}\n')

    lines.append(f'##########################################################################################\n')
    lines.append(f'# Hard-coded\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'# Wireload\n')
    lines.append(f'set wireload(name)       "wl10"\n')
    lines.append(f'set wireload(library)    "u055lscee12bdh_108c125_wc"\n')
    lines.append(f'\n')
    lines.append(f'# TLUPlus\n')
    lines.append(f'set TLUPlus_stdcell_max /projects/tropic01/pdk/umc/std_55_UM055LSCEE12BDH/0v1/tluplus/u055lscee12bdh_RCMAX.TLUPlus\n')
    lines.append(f'set TLUPlus_stdcell_min /projects/tropic01/pdk/umc/std_55_UM055LSCEE12BDH/0v1/tluplus/u055lscee12bdh_RCMIN.TLUPlus\n')
    lines.append(f'set MAP_stdcell         /projects/tropic01/pdk/umc/std_55_UM055LSCEE12BDH/0v1/map/UMC55_5m0t1f_TLUplus.map\n')
    lines.append(f'\n')
    lines.append(f'\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'# Hard-coded milkyway\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'\n')
    lines.append(f'set stdcell_tech "/projects/tropic01/pdk/umc/std_55_UM055LSCEE12BDH/0v1/tf/u055lscee12bdh_5m1t0f.tf"\n')
    lines.append(f'\n')
    lines.append(f'# Tcl file with library modifications for dont_use\n')
    lines.append(f'set LIBRARY_DONT_USE_FILE ""\n')
    lines.append(f'\n')
    lines.append(f'# Tcl file for customized dont use list before first compile\n')
    lines.append(f'set LIBRARY_DONT_USE_PRE_COMPILE_LIST ""\n')
    lines.append(f'\n')
    lines.append(f'# Tcl file with library modifications for dont_use before incr compile\n')
    lines.append(f'set LIBRARY_DONT_USE_PRE_INCR_COMPILE_LIST ""\n')
    lines.append(f'\n')
    lines.append(f'# Dont touch ts_common_blocks\n')
    lines.append(f'set DONT_TOUCH_TS_COMMON_BLOCKS true\n')
    lines.append(f'\n')
    lines.append(f'\n')
    lines.append(f'set MW_REFERENCE_LIB_DIRS $TS_MILKYWAY_VIEW_DIRS\n')
    lines.append(f'\n')
    lines.append(f'set NDM_REFERENCE_LIB_DIRS ""\n')
    lines.append(f'set MW_TECH_FILE $stdcell_tech\n')
    lines.append(f'\n')
    lines.append(f'\n')
    lines.append(f'\n')


    lines.append(f'##########################################################################################\n')
    lines.append(f'# Input file names/paths\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'\n')
    lines.append(f'# Script which is generated by ts_sim_compile.py which analyses RTL.\n')
    lines.append(f'set DCRM_RTL_READ_SCRIPT {TsGlobals.TS_SYN_RUN_DIR}/{TsGlobals.TS_SYN_SRC_RTL_FILE}\n')
    lines.append(f'\n')
    lines.append(f'# Constaints as an TCL, not SDC standard\n')
    lines.append(f'set DCRM_CONSTRAINTS_INPUT_FILE {get_repo_root_path()}/sdc/${{DESIGN_NAME}}_func.sdc\n')
    lines.append(f'\n')
    lines.append(f'# This variable points to where DC builds its internal design representation\n')
    lines.append(f'set TS_SYN_DIR {TsGlobals.TS_SYN_RUN_DIR}/build\n')
    lines.append(f'\n')
    lines.append(f'# Floopplan file\n')
    lines.append(f'set DCRM_DCT_DEF_INPUT_FILE {TsGlobals.TS_DESIGN_CFG["design"]["floorplan"]}\n')
    lines.append(f'\n')
    lines.append(f'\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'# Flow configuration\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'\n')
    lines.append(f'# Set variable OPTIMIZATION_FLOW from following RM+ flows\n')
    lines.append(f'# High Performance Low Power (hplp)\n')
    lines.append(f'# High Connectivity (hc)\n')
    lines.append(f'# Runtime Exploration (rtm_exp)\n')
    lines.append(f'\n')
    lines.append(f'# Specify one flow output of hllp | hc | rtm_exp | tim\n')
    lines.append(f'set OPTIMIZATION_FLOW "tim" \n')
    lines.append(f'\n')
    lines.append(f'# Use reduced effort for lower runtime in hplp and time flows (false | true)\n')
    lines.append(f'set REDUCES_EFFORT_OPTIMIZATION_FLOW "true "\n')
    lines.append(f'\n')
    lines.append(f'suppress_message UCN-1; # This is OK to suppress, only warning if multiple ports are connected to the same wire, no problem.\n') 
    lines.append(f'suppress_message TIM-164; # We cannot ensure all libraries to be characterized for common thresholds\n')
    lines.append(f'suppress_message TIM-175; # \n')
    lines.append(f'\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'# Flow breakpoints\n')
    lines.append(f'##########################################################################################\n')
    lines.append(f'\n')
    lines.append(f'# Generally, flow consists of following:\n')
    lines.append(f'#    1. Read in RTL, elaborate, link\n')
    lines.append(f'#    2. Read constraints\n')
    lines.append(f'#    3. Compile (synthesize)\n')
    lines.append(f'#    4. Write reports\n')
    lines.append(f'#\n')
    lines.append(f'# For debug, it is sometimes necessary to stop after some of these stesp and go back to\n')
    lines.append(f'# TCL command line of the synthesis tool. Following variables configure this:\n')
    lines.append(f'\n')
    lines.append(f'set BREAK_AFTER_LINK         "false"\n')
    lines.append(f'set BREAK_AFTER_CONSTRAINTS  "false"\n')
    lines.append(f'set BREAK_AFTER_COMPILE      "false"\n')
    lines.append(f'set BREAK_AFTER_REPORTS      "true"\n')
    lines.append(f'\n')
    lines.append(f'puts "RM-Info: Completed script [info script]"\n')
    lines.append(f'\n')

    # Create and write
    with open(path,'w') as setup_file:
        setup_file.writelines(lines)


def syn_open_design(args):
    """
    Generates dc run file for re-opening synthesis database
    : param args: arguments
    """
    # Empty buffer - generation to be line by line
    lines = []

    lines.append(f'\n')
    lines.append(f'\n')
    lines.append(f'source -echo -verbose $env(TS_SYN_FLOW_PATH)/common/dc_setup.tcl\n') 
    lines.append(f'set_app_var case_analysis_propagate_through_icg true\n')
    lines.append(f'read_file -format ddc ${{RESULTS_DIR}}/${{DCRM_FINAL_DDC_OUTPUT_FILE}}\n')
    lines.append(f'\n')

    # Create and write
    with open(TsGlobals.TS_SYN_DC_RM_OPENFILE,'w') as run_file:
        run_file.writelines(lines)