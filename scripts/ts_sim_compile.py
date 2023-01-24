#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square compilation script for digital simulations
#
# TODO: License
####################################################################################################

__author__ = "Ondrej Ille"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Ondrej Ille"

import os
import shutil
import sys

import argcomplete
from internal.ts_hw_args import (
    TsArgumentParser,
    add_cfg_files_arg,
    add_target_arg,
    add_ts_common_args,
    add_ts_sim_compile_args,
)
from internal.ts_hw_cfg_parser import (
    do_design_config_init,
    do_sim_config_init,
    print_target_list,
)
from internal.ts_hw_common import check_target, init_signals_handler, ts_get_cfg
from internal.ts_hw_export import export_dc_tcl, export_vivado_tcl
from internal.ts_hw_global_vars import TsGlobals
from internal.ts_hw_hooks import TsHooks, ts_call_global_hook
from internal.ts_hw_logging import (
    TsColors,
    TsErrCode,
    TsInfoCode,
    ts_configure_logging,
    ts_debug,
    ts_info,
    ts_print,
    ts_throw_error,
)
from internal.ts_hw_simulator_ifc import ts_sim_compile
from internal.ts_hw_source_list_files import (
    load_source_list_files,
    print_source_file_list,
)


def sim_compile(arguments):

    args = {
        "clear": False,
        "list_targets": False,
        "list_sources": False,
        "exp_tcl_file_dc": False,
        "exp_tcl_file_vivado": False,
        **vars(arguments),
    }

    # Check target
    check_target(args["target"])

    # Loading source list files for a target
    ts_info(TsInfoCode.INFO_CMN_3, args["target"])

    load_source_list_files(args["target"])

    # Print list of targets
    if args["list_targets"]:
        print_target_list()
        return 0

    # Print list of source files
    if args["list_sources"]:
        print_source_file_list()
        return 0

    # Check we are not in build directory itself
    ts_debug("Checking we are not in build directory itself...")
    ts_debug("Current dir is {}".format(os.getcwd()))
    ts_debug("Build dir is {}".format(ts_get_cfg("build_dir")))
    if os.getcwd() == ts_get_cfg("build_dir"):
        ts_throw_error(TsErrCode.ERR_CMP_4, ts_get_cfg("build_dir"))

    ts_debug("Clear build directory before building")
    if args["clear"]:
        shutil.rmtree(ts_get_cfg("build_dir"), ignore_errors=True)
    

    ################################################################################################
    # Export of synthesis TCL files
    ################################################################################################
    if args["exp_tcl_file_dc"]:
        ts_print(f"Exporting dc_shell TCL file: {args['exp_tcl_file_dc']}",
                    color=TsColors.PURPLE, big=True)
        export_dc_tcl(args["exp_tcl_file_dc"])
        return 0

    if args["exp_tcl_file_vivado"]:
        ts_print(f"Exporting vivado TCL file: {args['exp_tcl_file_vivado']}",
                    color=TsColors.PURPLE, big=True)
        export_vivado_tcl(args["exp_tcl_file_vivado"])
        return 0

    ################################################################################################
    # Compilation
    ################################################################################################
    ts_call_global_hook(TsHooks.PRE_COMPILE)

    ts_sim_compile()

    ts_call_global_hook(TsHooks.POST_COMPILE)
    return 0


if __name__ == "__main__":

    init_signals_handler()

    # Add script arguments
    parser = TsArgumentParser(description="HDL compilation script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_ts_sim_compile_args(parser)
    add_target_arg(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    TsGlobals.TS_SIM_CFG_PATH = args.sim_cfg
    ts_configure_logging(args)

    # Load config files, merge with args and check configuration
    do_sim_config_init(args)
    do_design_config_init(args)

    # Launch compilation
    sys.exit(sim_compile(args))

