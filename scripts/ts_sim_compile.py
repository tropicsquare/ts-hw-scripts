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

import shutil
import os
import sys
import argcomplete

from internal import *


def sim_compile(arguments):

    args = {
        'clear': False,
        'list_targets': False,
        'list_sources': False,
        'exp_tcl_file_dc': False,
        'exp_tcl_file_vivado': False,
        **vars(arguments)
    }

    # Check target
    check_target(args["target"])

    # Loading source list files for a target
    ts_info(TsInfoCode.INFO_CMN_3, args["target"])

    TsGlobals.TS_SIM_SRCS = load_source_list_files(args["target"])
    TsGlobals.TS_SIM_SRCS_BY_LIB = group_source_list_files_by_lib(TsGlobals.TS_SIM_SRCS)

    # Print list of targets
    if args["list_targets"]:
        print_target_list()
        return 0

    # Print list of source files
    if args["list_sources"]:
        print_source_file_list(True)
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
        ts_big_info(TsInfoCode.INFO_CMN_24, "dc_shell", args["exp_tcl_file_dc"])
        export_dc_tcl(args["exp_tcl_file_dc"])
        return 0

    if args["exp_tcl_file_vivado"]:
        ts_big_info(TsInfoCode.INFO_CMN_24, "vivado", args["exp_tcl_file_vivado"])
        export_vivado_tcl(args["exp_tcl_file_vivado"])
        return 0

    ################################################################################################
    # Compilation
    ################################################################################################
    ts_call_global_hook(TsHooks.PRE_COMPILE)

    # Run compilation
    ts_big_info(TsInfoCode.INFO_CMN_6)
    ts_sim_compile()
    ts_big_info(TsInfoCode.INFO_CMN_7)

    ts_call_global_hook(TsHooks.POST_COMPILE)
    return 0


if __name__ == "__main__":

    init_signals_handler()

    # Add script arguments
    parser = argparse.ArgumentParser(description="HDL compilation script")
    add_ts_common_args(parser)
    add_ts_sim_compile_args(parser)
    add_target_arg(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    TsGlobals.TS_SIM_CFG_PATH = args.sim_cfg
    ts_configure_logging(args)

    # Load config file, merge with args and check configuration
    do_config_init(args)

    # Launch compilation
    sys.exit(sim_compile(args))

