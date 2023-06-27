#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square place and route script
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
    add_ts_pnr_run_args,
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
from internal.ts_hw_pnr_support import (
    build_icc2_cmd,
    create_pnr_sub_dirs,
    delete_pnr_sub_dir,
    open_result_test,
    pnr_design_cfg_file,
    pnr_logging,
    pnr_mcmm_file,
    pnr_open_design,
    pnr_setup,
    release,
    set_license_queuing,
    set_license_wait_time,
    set_pnr_global_vars,
)
from internal.ts_hw_source_list_files import load_source_list_files

if __name__ == "__main__":

    init_signals_handler()

    ################################################################################################
    # Parse arguments
    ################################################################################################
    parser = TsArgumentParser(description="ICC2 script")

    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_runcode_arg(parser)
    add_lic_wait_arg(parser, "icc2_shell")
    add_stayin_arg(parser, "icc2_shell")
    add_ts_pnr_run_args(parser, "icc2_shell")
    add_force_arg(parser)
    add_release_arg(parser)
    add_pd_common_args(parser)
    add_source_data_arg(parser)
    add_batch_mode_arg(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Prepare file handler
    pnr_logging(args)

    # Do Config Init
    # Config for ts_design_cfg
    setattr(args, "filter_mode_usage", "pnr")
    do_design_config_init(args, enforce=True)
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
    # check_valid_mode_arg(args)

    # Check existance of runcode - runcode is also name of run dir TS_REPO_ROOT/pnr/{runcode}
    if args.runcode is None:
        ts_throw_error(TsErrCode.ERR_PNR_0)
    else:
        ts_info(TsInfoCode.INFO_PNR_0, args.runcode)
        # Set PnR flow global variables
        set_pnr_global_vars(args)

    # Check if user requires either to run new PnR or to open existing PnR database
    if args.open_result is False:
        if args.force is True:
            ts_info(TsInfoCode.INFO_PNR_2, TsGlobals.TS_PNR_RUNCODE)
            # Delete DIR of runcode name if exists
            delete_pnr_sub_dir()
        else:
            # Test if database already exists, otherwise create sub-folder
            if open_result_test(args) is True:
                ts_throw_error(TsErrCode.ERR_PNR_2, TsGlobals.TS_PNR_RUNCODE)

        # Create new sub-folder with name of runcode
        create_pnr_sub_dirs()

    else:
        # Open database
        if open_result_test(args) is True:
            ts_info(TsInfoCode.INFO_PNR_1, TsGlobals.TS_PNR_RUNCODE)
            pnr_open_design(args)
        # If doesn't exist then error
        else:
            ts_throw_error(TsErrCode.ERR_PNR_1, TsGlobals.TS_PNR_RUNCODE)

    # Generates design configuration tcl file
    pnr_design_cfg_file(args)

    # Generate pnr setup tcl file
    pnr_setup(os.path.join(TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_SETUP_FILE), args)

    # Generate pnr mmcm setup tcl file
    pnr_mcmm_file(
        os.path.join(TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_MCMM_FILE), args
    )

    # Set enviromental variable for PNR - license quering
    set_license_queuing(args, "icc2_shell", "SNPSLMD_QUEUE")
    set_license_wait_time(args, "icc2_shell", "SNPS_MAX_WAITTIME", "1")
    set_license_wait_time(args, "icc2_shell", "SNPS_MAX_QUEUETIME", "1")

    # Prepare pnr_cmd
    icc2_cmd = build_icc2_cmd(args)

    # Run PnR
    exec_cmd_in_dir(
        directory=TsGlobals.TS_PNR_RUN_DIR, command=icc2_cmd, batch_mode=args.batch_mode
    )

    # Goodbye place and route!
    ts_print("PnR is done!", color=TsColors.PURPLE, big=True)

    # Release data to a given flow_dir - pnr
    if (
        args.release
        and TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["pnr"]
        and not args.force
    ):
        TsGlobals.TS_PNR_RELEASE_DIR = os.path.join(
            ts_get_root_rel_path(
                TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["pnr"],
                TsGlobals.TS_PNR_RUNCODE,
            )
        )
        release(TsGlobals.TS_PNR_RUN_DIR, TsGlobals.TS_PNR_RELEASE_DIR, "pnr")

sys.exit(0)
