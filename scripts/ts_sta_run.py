#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square static timing analysis main script
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
    parser = TsArgumentParser(description="STA script")

    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_runcode_arg(parser)
    add_lic_wait_arg(parser,"pt_shell")
    add_stayin_arg(parser,"pt_shell")
    add_ts_sta_run_args(parser,"pt_shell")
    add_force_arg(parser)
    add_source_data_arg(parser,"syn")
    add_release_arg(parser)
    
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Prepare file handler
    sta_logging(args)

    # Do Config Init
    # Config for ts_design_cfg
    do_design_config_init(args)
    # Target need to be defined from TS_DESIGN_CFG (holder of value)
    setattr(args, "target", TsGlobals.TS_DESIGN_CFG["design"]["target"])
    # Sim cfg needed for usage of TS_SIM_CFG variable (holder of design name)
    do_sim_config_init(args)
    check_valid_design_target()
    # Execute load of source list according to selected target - ts_hw_souce_list_files
    load_source_list_files(args.target)

    # Check --source selector valitity
    check_valid_source_data_arg(args)

    # Check --mode selector validity
    check_valid_mode_arg(args)

    # Check existance of runcode - runcode is also name of run dir TS_REPO_ROOT/sta/{runcode}
    if args.runcode is None:
        ts_throw_error(TsErrCode.ERR_STA_0)
    else: 
        ts_info(TsInfoCode.INFO_STA_0,args.runcode)
        # Set sta flow global variables
        set_sta_global_vars(args)

    # Check dmsa vs mode selector usage
    if not (bool(args.dmsa) ^ bool(args.mode)):
        ts_throw_error(TsErrCode.ERR_STA_6)

    # Check dmsa vs open selector usage
    if (bool(args.dmsa) and bool(args.open_result)):
        ts_throw_error(TsErrCode.ERR_STA_7)

    # Check if user requires either to run new synthesis or to open existing synthesis database
    if args.open_result is False:
        if args.force is True:
            ts_info(TsInfoCode.INFO_STA_2,TsGlobals.TS_STA_RUNCODE)
            # Delete DIR of runcode name if exists
            delete_sta_sub_dir()
        else:
            # Test if database already exists, otherwise create sub-folder
            if runcode_dir_test(args) is True:
                ts_throw_error(TsErrCode.ERR_STA_2,TsGlobals.TS_STA_RUNCODE)

        # Create new sub-folder with name of runcode
        create_sta_sub_dirs()

    else:
        # Open database
        if runcode_dir_test(args) is True:
            ts_info(TsInfoCode.INFO_STA_1,TsGlobals.TS_STA_RUNCODE)
            sta_open_design(args)
        # If doesn't exist then error
        else:
            ts_throw_error(TsErrCode.ERR_STA_1,TsGlobals.TS_STA_RUNCODE)



    # Generates design configuration tcl file
    sta_design_cfg_file(args)

    # Generate synthesis setup tcl file
    sta_setup(TsGlobals.TS_STA_SETUP_FILE, args)

    # Generate synthesis dmsa setup tcl file
    if args.dmsa:
        sta_dmsa_file(TsGlobals.TS_STA_DMSA_FILE, args)

    # Set enviromental variable for DC - license quering
    set_license_queuing(args,"pt_shell","SNPSLMD_QUEUE")

    # Prepare pt_cmd
    pt_cmd = build_sta_cmd(args)

    # Run STA
    exec_cmd_in_dir_interactive(TsGlobals.TS_STA_RUN_DIR,pt_cmd)

    # Goodbye STA!
    ts_print("STA is done!",color=TsColors.PURPLE,big=True)

    # Release data to a given flow_dir - sta
    if args.release and TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["sta"] and not args.force:
        TsGlobals.TS_STA_RELEASE_DIR = join(ts_get_root_rel_path(TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["sta"],TsGlobals.TS_STA_RUNCODE))
        release(TsGlobals.TS_STA_RUN_DIR,TsGlobals.TS_STA_RELEASE_DIR,"sta")

sys.exit(0)
