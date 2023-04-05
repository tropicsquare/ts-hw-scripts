#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square ts_dft_run.py dft script
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
    add_cfg_files_arg,
    add_dft_lint_args,
    add_force_arg,
    add_lic_wait_arg,
    add_pd_common_args,
    add_release_arg,
    add_runcode_arg,
    add_source_data_arg,
    add_stayin_arg,
    add_ts_common_args,
)
from internal.ts_hw_cfg_parser import (
    check_valid_design_target,
    do_design_config_init,
    do_dft_lint_init,
    do_sim_config_init,
)
from internal.ts_hw_common import (
    exec_cmd_in_dir,
    init_signals_handler,
    ts_get_root_rel_path,
)
from internal.ts_hw_dft_support import (
    build_lint_cmd,
    create_dft_subdirs,
    delete_dft_subdirs,
    dft_logging,
    dft_runfile,
    get_dft_rootdir,
    lint_design_cfg,
    lint_setup_file,
    lint_src_file,
    set_dft_global_vars,
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

if __name__ == "__main__":

    init_signals_handler()

    ################################################################################################
    # Parse arguments
    ################################################################################################
    parser = argparse.ArgumentParser(description="Main DFT flow script")

    # Sub-parsers
    subparsers = parser.add_subparsers(
        title="Available DFT flow types",
        description="lint - formal verification in spyglass, atpg - automatic test pattern generatior, rtl - insert dft structures into RTL",
    )

    # LINT parser
    parser_lint = subparsers.add_parser("lint")
    parser_lint.set_defaults(flow="dft-lint")
    parser_lint.set_defaults(filter_mode_usage="dft-lint")
    add_runcode_arg(parser_lint)
    add_dft_lint_args(parser_lint, TsGlobals.TS_DFT_LINT_TOOL)
    add_release_arg(parser_lint)
    add_source_data_arg(parser_lint, "dft-lint")
    add_stayin_arg(parser_lint, TsGlobals.TS_DFT_LINT_TOOL)
    add_force_arg(parser_lint)
    add_cfg_files_arg(parser_lint)
    add_ts_common_args(parser_lint)

    # ATPG parser
    parser_atpg = subparsers.add_parser("atpg")
    parser_atpg.set_defaults(flow="dft-atpg")
    parser_atpg.set_defaults(filter_mode_usage="dft-atpg")
    add_stayin_arg(parser_atpg, TsGlobals.TS_DFT_ATPG_TOOL)

    # RTL parser
    parser_rtl = subparsers.add_parser("rtl", description="DFT RTL insertion flow")
    parser_rtl.set_defaults(flow="dft-rtl")
    add_stayin_arg(parser_rtl, TsGlobals.TS_DFT_RTL_TOOL)

    # Process args
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    ts_configure_logging(args)

    # Prepare file handler
    dft_logging(args)

    # Do Config Init
    # Config for ts_design_cfg
    do_design_config_init(args, enforce=True)

    # Target need to be defined from TS_DESIGN_CFG (holder of value)
    setattr(args, "target", TsGlobals.TS_DESIGN_CFG["design"]["target"])

    # Sim cfg needed for usage of TS_SIM_CFG variable (holder of design name)
    do_sim_config_init(args, skip_check=False, merge_args_to_config=False)
    check_valid_design_target()

    # Execute load of source list according to selected target - ts_hw_souce_list_files
    load_source_list_files(args.target)

    # Process args for lint
    do_dft_lint_init(args)

    # Check existance of runcode - runcode is also name of run dir TS_REPO_ROOT/syn/{runcode}
    if args.runcode is None:
        ts_throw_error(TsErrCode.ERR_DFT_0)
    else:
        ts_info(TsInfoCode.INFO_DFT_0, args.runcode)
        # Set synthesis flow global variables
        set_dft_global_vars(args)

    # Check if user requires either to run new synthesis or to open existing synthesis database
    if args.open_result is False:
        if args.force is True:
            ts_info(TsInfoCode.INFO_SYS_2, args.runcode)
            # Delete DIR of runcode name if exists
            delete_dft_subdirs()
        else:
            # Test if database already exists, otherwise create sub-folder
            if (
                os.path.isdir(
                    os.path.join(get_dft_rootdir(args), TsGlobals.TS_DFT_RUNCODE)
                )
                is True
            ):
                ts_throw_error(TsErrCode.ERR_SYN_2, args.runcode)

        # Create new sub-folder with name of runcode
        create_dft_subdirs()

    else:
        # Open database
        if (
            os.path.isdir(os.path.join(get_dft_rootdir(args), TsGlobals.TS_DFT_RUNCODE))
            is True
        ):
            ts_info(TsInfoCode.INFO_SYS_1, args.runcode)
            syn_open_design(args)
        # If doesn't exist then error
        else:
            ts_throw_error(TsErrCode.ERR_SYN_1, args.runcode)

    if args.flow == "dft-lint":

        # Generates necessary source files
        lint_src_file()

        # Generates dft run file
        dft_runfile(args)

        # Generates design configuration tcl file
        lint_design_cfg(args)

        # Generate lint setup tcl file
        lint_cmd = lint_setup_file(args)
        exec_cmd_in_dir(TsGlobals.TS_DFT_RUN_DIR, lint_cmd, args.batch_mode)

        # Prepare lint_cmd
        # Uses dft runfile
        lint_cmd = build_lint_cmd(args)

        # Run LINT
        exec_cmd_in_dir(TsGlobals.TS_DFT_RUN_DIR, lint_cmd, args.batch_mode)

        # Goodbye synthesis!
        ts_print("DFT is done!", color=TsColors.PURPLE, big=True)
    else:
        ts_print("DFT cannot be run!", color=TsColors.PURPLE, big=True)

sys.exit(0)
