#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square dc_shell synthesis script
#
# Options
# scenario (scenario(s) to run)
# --runcode <runcode>
#
# TODO: License
####################################################################################################

__author__ = "Jan Zapeca"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Jan Zapeca"

import shutil
import os
import argcomplete
from internal import *


if __name__ == "__main__":

    init_signals_handler()

    ################################################################################################
    # Parse arguments
    ################################################################################################
    parser = TsArgumentParser(description="Design compiler shell script")

    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_runcode_arg(parser)
    add_lic_wait_arg(parser,"dc_shell")
    add_stayin_arg(parser,"dc_shell")
    add_ts_syn_run_args(parser,"dc_shell")
    add_force_arg(parser)
    add_release_arg(parser)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Prepare file handler
    syn_logging(args)

    # Do Config Init
    # Config for ts_design_cfg
    #setattr(args, "design_cfg", join(get_repo_root_path(),TsGlobals.TS_DESIGN_CFG_PATH))
    do_design_config_init(args, enforce=True)
    # Target need to be defined from TS_DESIGN_CFG (holder of value)
    setattr(args, "target", TsGlobals.TS_DESIGN_CFG["design"]["target"])
    # Sim cfg needed for usage of TS_SIM_CFG variable (holder of design name)
    do_sim_config_init(args)
    check_valid_design_target()
    # Execute load of source list according to selected target - ts_hw_souce_list_files
    load_source_list_files(args.target)


    # Check existance of runcode - runcode is also name of run dir TS_REPO_ROOT/syn/{runcode}
    if args.runcode is None:
        ts_throw_error(TsErrCode.ERR_SYN_0)
    else:
        ts_info(TsInfoCode.INFO_SYS_0,args.runcode)
        # Set synthesis flow global variables
        set_syn_global_vars(args)

    # Check if user requires either to run new synthesis or to open existing synthesis database
    if args.open_result is False:
        if args.force is True:
            ts_info(TsInfoCode.INFO_SYS_2,args.runcode)
            # Delete DIR of runcode name if exists
            delete_syn_sub_dir()
        else:
            # Test if database already exists, otherwise create sub-folder
            if open_result_test(args) is True:
                ts_throw_error(TsErrCode.ERR_SYN_2,args.runcode)

        # Create new sub-folder with name of runcode
        create_syn_sub_dirs()

        # Generates RTL source tcl file
        syn_rtl_src_file(args)

    else:
        # Open database
        if open_result_test(args) is True:
            ts_info(TsInfoCode.INFO_SYS_1,args.runcode)
            syn_open_design(args)
        # If doesn't exist then error
        else:
            ts_throw_error(TsErrCode.ERR_SYN_1,args.runcode)



    # Generates design configuration tcl file
    syn_design_cfg_file(args)

    # Generate synthesis setup tcl file
    syn_setup(join(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_SETUP_FILE), args)

    # Generate synthesis mmcm setup tcl file
    syn_mcmm_file(join(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_MCMM_FILE), args)

    # Set enviromental variable for DC - license quering
    set_license_queuing(args,"dc_shell","SNPSLMD_QUEUE")

    # Prepare dc_cmd
    dc_cmd = build_synthesis_cmd(args)

    # Run DC
    exec_cmd_in_dir_interactive(TsGlobals.TS_SYN_RUN_DIR,dc_cmd)

    # Goodbye synthesis!
    ts_print("Synthesis is done!", color=TsColors.PURPLE, big=True)

    # Release data to a given flow_dir - syn
    if args.release and TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["syn"] and not args.force:
        TsGlobals.TS_SYN_RELEASE_DIR = join(ts_get_root_rel_path(TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["syn"],args.runcode))
        release(TsGlobals.TS_SYN_RUN_DIR,TsGlobals.TS_SYN_RELEASE_DIR,"syn")

sys.exit(0)
