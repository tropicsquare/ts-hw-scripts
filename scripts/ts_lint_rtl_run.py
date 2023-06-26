#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square ts_lint_rtl_run.py dft script
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

import argparse
import os
import sys

import argcomplete
from internal.ts_hw_args import (
    TsArgumentParser,
    add_batch_mode_arg,
    add_cfg_files_arg,
    add_force_arg,
    add_lic_wait_arg,
    add_lint_rtl_args,
    add_release_arg,
    add_runcode_arg,
    add_source_data_arg,
    add_stayin_arg,
    add_ts_common_args,
)
from internal.ts_hw_cfg_parser import (
    check_valid_design_target,
    do_design_config_init,
    do_lint_init,
    do_sim_config_init,
)
from internal.ts_hw_common import (
    exec_cmd_in_dir,
    init_signals_handler,
    ts_get_root_rel_path,
)
from internal.ts_hw_global_vars import TsGlobals
from internal.ts_hw_lint_rtl_support import (
    build_lint_cmd,
    create_rtl_lint_subdirs,
    delete_rtl_lint_subdirs,
    get_rootdir,
    lint_design_cfg,
    lint_setup_file,
    lint_src_file,
    open_design,
    rtl_lint_logging,
    rtl_lint_runfile,
    set_rtl_lint_global_vars,
)
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

if __name__ == "__main__":

    init_signals_handler()

    ################################################################################################
    # Parse arguments
    ################################################################################################
    parser = TsArgumentParser(description="Main LINT RTL script")

    # LINT parser
    add_runcode_arg(parser)
    add_lint_rtl_args(parser, TsGlobals.TS_RTL_LINT_TOOL)
    add_release_arg(parser)
    add_batch_mode_arg(parser)
    add_source_data_arg(parser, "rtl_lint")
    add_stayin_arg(parser, TsGlobals.TS_RTL_LINT_TOOL)
    add_force_arg(parser)
    add_cfg_files_arg(parser)
    add_ts_common_args(parser)

    # Process args
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    ts_configure_logging(args)

    # Prepare file handler
    rtl_lint_logging(args)

    # Do Config Init
    # Config for ts_design_cfg
    do_design_config_init(args, enforce=True)

    # Target need to be defined from TS_DESIGN_CFG (holder of value)
    setattr(args, "target", TsGlobals.TS_DESIGN_CFG["design"]["target"])

    # Set flow_type
    setattr(args, "flow", "rtl_lint")

    # Sim cfg needed for usage of TS_SIM_CFG variable (holder of design name)
    do_sim_config_init(args)
    check_valid_design_target()

    # Execute load of source list according to selected target - ts_hw_souce_list_files
    load_source_list_files(args.target)

    # Process args for lint
    do_lint_init(args)

    # Check existance of runcode - runcode is also name of run dir TS_REPO_ROOT/lint/{tool}/{runcode}
    if args.runcode is None:
        ts_throw_error(TsErrCode.ERR_DFT_0)
    else:
        ts_info(TsInfoCode.INFO_DFT_0, args.runcode)
        # Set the flow global variables
        set_rtl_lint_global_vars(args)

    # Check if user requires either to run new lint or to open existing lint database
    if args.open_result is False:
        if args.force is True:
            ts_info(TsInfoCode.INFO_SYS_2, args.runcode)
            # Delete DIR of runcode name if exists
            delete_rtl_lint_subdirs()
        else:
            # Test if database already exists, otherwise create sub-folder
            if (
                os.path.isdir(
                    os.path.join(get_dft_rootdir(args), TsGlobals.TS_RTL_LINT_RUNCODE)
                )
                is True
            ):
                ts_throw_error(TsErrCode.ERR_SYN_2, args.runcode)

        # Create new sub-folder with name of runcode
        create_rtl_lint_subdirs()

    else:
        # Open database
        if (
            os.path.isdir(
                os.path.join(get_rootdir(args), TsGlobals.TS_RTL_LINT_RUNCODE)
            )
            is True
        ):
            ts_info(TsInfoCode.INFO_SYS_1, args.runcode)
            open_design_cmd = open_design(args)
            exec_cmd_in_dir(
                TsGlobals.TS_RTL_LINT_RUN_DIR, open_design_cmd, args.batch_mode
            )
            sys.exit(0)
        # If doesn't exist then error
        else:
            ts_throw_error(TsErrCode.ERR_SYN_1, args.runcode)

    # Generates necessary source files
    lint_src_file()

    # Generates dft run file
    rtl_lint_runfile(args)

    # Generates design configuration tcl file
    lint_design_cfg(args)

    # Generate lint setup tcl file
    lint_cmd = lint_setup_file(args)
    exec_cmd_in_dir(TsGlobals.TS_RTL_LINT_RUN_DIR, lint_cmd, args.batch_mode)

    # Prepare lint_cmd
    # Uses dft runfile
    lint_cmd = build_lint_cmd(args)

    # Run LINT
    exec_cmd_in_dir(TsGlobals.TS_RTL_LINT_RUN_DIR, lint_cmd, args.batch_mode)

    # Goodbye message
    ts_print("LINT RTL is done!", color=TsColors.PURPLE, big=True)

sys.exit(0)
