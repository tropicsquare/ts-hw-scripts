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

import os
import sys

import argcomplete
from internal.ts_hw_args import (
    TsArgumentParser,
    add_batch_mode_arg,
    add_cfg_files_arg,
    add_force_arg,
    add_lic_wait_arg,
    add_pd_common_args,
    add_release_arg,
    add_runcode_arg,
    add_source_data_arg,
    add_stayin_arg,
    add_ts_common_args,
    add_ts_sta_run_args,
)
from internal.ts_hw_cfg_parser import (
    check_valid_design_target,
    check_valid_mode_arg,
    check_valid_source_data_arg,
    do_design_config_init,
    do_sim_config_init,
)
from internal.ts_hw_common import (
    exec_cmd_in_dir,
    init_signals_handler,
    ts_get_root_rel_path,
)
from internal.ts_hw_check import (
    check_snps_log_file
)
from internal.ts_hw_global_vars import TsGlobals
from internal.ts_hw_logging import (
    TsColors,
    TsErrCode,
    TsInfoCode,
    ts_configure_logging,
    ts_info,
    ts_print,
    ts_throw_error,
)
from internal.ts_hw_source_list_files import load_source_list_files
from internal.ts_hw_sta_support import (
    build_sta_cmd,
    create_sta_sub_dirs,
    delete_sta_sub_dir,
    runcode_dir_test,
    set_sta_global_vars,
    sta_design_cfg_file,
    sta_dmsa_file,
    sta_logging,
    sta_open_design,
    sta_setup,
)
from internal.ts_hw_syn_support import release, set_license_queuing

if __name__ == "__main__":

    init_signals_handler()

    ################################################################################################
    # Parse arguments
    ################################################################################################
    parser = TsArgumentParser(description="STA script")

    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_runcode_arg(parser)
    add_lic_wait_arg(parser, "pt_shell")
    add_stayin_arg(parser, "pt_shell")
    add_ts_sta_run_args(parser, "pt_shell")
    add_force_arg(parser)
    add_source_data_arg(parser, "syn")
    add_release_arg(parser)
    add_pd_common_args(parser)
    add_batch_mode_arg(parser)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Prepare file handler
    sta_logging(args)

    # Do Config Init
    # Config for ts_design_cfg
    if args.sign_off:
        setattr(args, "filter_mode_usage", "sta-signoff")
    elif args.open_result:
        # Do not filter for open design
        setattr(args, "filter_mode_usage", None)
    else:
        setattr(args, "filter_mode_usage", "sta")

    do_design_config_init(args)
    # Target need to be defined from TS_DESIGN_CFG (holder of value)
    setattr(args, "target", TsGlobals.TS_DESIGN_CFG["design"]["target"])
    # Sim cfg needed for usage of TS_SIM_CFG variable (holder of design name)
    do_sim_config_init(args)
    check_valid_design_target()
    # Execute load of source list according to selected target - ts_hw_souce_list_files
    load_source_list_files(args.target)

    # Check --source selector validity
    check_valid_source_data_arg(args)

    # Check --mode selector validity
    check_valid_mode_arg(args)

    # Check existance of runcode - runcode is also name of run dir TS_REPO_ROOT/sta/{runcode}
    if args.runcode is None:
        ts_throw_error(TsErrCode.ERR_STA_0)
    else:
        ts_info(TsInfoCode.INFO_STA_0, args.runcode)
        # Set sta flow global variables
        set_sta_global_vars(args)

    # dmsa
    #   no open-result
    #   no mode - mutual exclusivity

    # open-result
    #   no dmsa
    #   mode is possible

    if bool(args.open_result) & bool(args.dmsa):
        ts_throw_error(TsErrCode.ERR_STA_7)
    elif not bool(args.open_result) and not (bool(args.dmsa) ^ bool(args.mode)):
        ts_throw_error(TsErrCode.ERR_STA_6)

    # Check if user requires either running a new sta or opennig an existing sta session database
    if args.open_result is False:
        if args.force is True:
            ts_info(TsInfoCode.INFO_STA_2, TsGlobals.TS_STA_RUNCODE)
            # Delete DIR of runcode name if exists
            delete_sta_sub_dir()
        else:
            # Test if database already exists, otherwise create sub-folder
            if runcode_dir_test(args) is True:
                ts_throw_error(TsErrCode.ERR_STA_2, TsGlobals.TS_STA_RUNCODE)

        # Create new sub-folder with name of runcode
        create_sta_sub_dirs()

    else:
        # Open database
        if runcode_dir_test(args) is True:
            ts_info(TsInfoCode.INFO_STA_1, TsGlobals.TS_STA_RUNCODE)
            sta_open_design(args)
        # If doesn't exist then error
        else:
            ts_throw_error(TsErrCode.ERR_STA_1, TsGlobals.TS_STA_RUNCODE)

    # Generates design configuration tcl file
    sta_design_cfg_file(args)

    # Generate static timing analysis setup tcl file
    sta_setup(TsGlobals.TS_STA_SETUP_FILE, args)

    # Generate static timing analysis dmsa setup tcl file
    if args.dmsa:
        sta_dmsa_file(TsGlobals.TS_STA_DMSA_FILE, args)

    # Set enviromental variable for DC - license quering
    set_license_queuing(args, "pt_shell", "SNPSLMD_QUEUE")

    # Prepare pt_cmd
    [pt_cmd, log_file] = build_sta_cmd(args)

    # Run STA
    exec_cmd_in_dir(
        directory=TsGlobals.TS_STA_RUN_DIR, command=pt_cmd, batch_mode=args.batch_mode
    )

    exit_code = check_snps_log_file("STA", log_file)

    # Goodbye STA!
    ts_print("STA is done!", color=TsColors.PURPLE, big=True)

    # Release data to a given flow_dir - sta
    if (
        args.release
        and TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["sta"] is not None
        and not args.force
    ):
        TsGlobals.TS_STA_RELEASE_DIR = os.path.join(
            ts_get_root_rel_path(
                TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["sta"],
                TsGlobals.TS_STA_RUNCODE,
            )
        )
        release(TsGlobals.TS_STA_RUN_DIR, TsGlobals.TS_STA_RELEASE_DIR, "sta")

    sys.exit(exit_code)
