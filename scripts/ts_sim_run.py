#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square Simulation script for digital simulations
#
# TODO: License
####################################################################################################

__author__ = "Ondrej Ille"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Ondrej Ille"

import shutil
import sys

import argcomplete
from internal.ts_hw_args import (
    TsArgumentParser,
    add_cfg_files_arg,
    add_target_arg,
    add_ts_common_args,
    add_ts_sim_run_args,
    add_pd_common_args,
)

from internal.ts_hw_cfg_parser import do_design_config_init, do_sim_config_init
from internal.ts_hw_common import (
    check_target,
    create_sim_sub_dir,
    init_signals_handler,
    ts_generate_seed,
    ts_get_cfg,
    ts_get_root_rel_path,
)
from internal.ts_hw_global_vars import TsGlobals
from internal.ts_hw_hooks import TsHooks, ts_call_global_hook, ts_call_local_hook
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
from internal.ts_hw_simulator_ifc import ts_sim_elaborate, ts_sim_run
from internal.ts_hw_test_list_files import get_test_list, get_tests_to_run, load_tests
from ts_sim_check import sim_check
from ts_sim_compile import sim_compile

if __name__ == "__main__":

    init_signals_handler()

    # Add script arguments
    parser = TsArgumentParser(description="Digital simulation script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_target_arg(parser)
    add_ts_sim_run_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    TsGlobals.TS_SIM_CFG_PATH = args.sim_cfg
    ts_configure_logging(args)

    # Load config file, merge with args and check configuration
    do_sim_config_init(args, skip_check=False, merge_args_to_config=True)
    do_design_config_init(args)

    # Re-compile if "recompile" is set
    if ts_get_cfg("recompile"):
        ts_info(TsInfoCode.INFO_CMN_23)
        ret_val = sim_compile(args)
        if ret_val != 0:
            sys.exit(ret_val)

    # Check target
    check_target(args.target)

    # Load available tests
    load_tests()

    # Print available tests and exit
    if args.list_tests:
        ts_print("Tests available:", *get_test_list(TsGlobals.TS_TEST_LIST), sep="\n\t")
        sys.exit(0)

    # Check that no test is given as a special option
    if not args.test_name:
        ts_throw_error(TsErrCode.ERR_SLF_15)

    # Find tests to be executed
    if len(get_tests_to_run(args.test_name)) == 0:
        ts_throw_error(TsErrCode.ERR_SLF_14, str(args.test_name))

    # Print tests to be executed
    ts_info(TsInfoCode.INFO_CMN_13, get_test_list(TsGlobals.TS_TEST_RUN_LIST))
    ts_info(
        TsInfoCode.GENERIC, f"Each test will be executed {ts_get_cfg('loop')} time(s)"
    )
    ts_call_global_hook(TsHooks.PRE_RUN)

    # Clear log directories if user wants
    if ts_get_cfg("clear_logs"):
        shutil.rmtree(
            ts_get_root_rel_path(TsGlobals.TS_ELAB_LOG_DIR_PATH), ignore_errors=True
        )
        shutil.rmtree(
            ts_get_root_rel_path(TsGlobals.TS_SIM_LOG_DIR_PATH), ignore_errors=True
        )

    # Create sim_logs, elab_logs directories
    ts_debug("Create 'sim_logs' directory (if it does not exist)")
    create_sim_sub_dir(TsGlobals.TS_SIM_LOG_DIR_PATH)
    ts_debug("Create elaboration log directory")
    create_sim_sub_dir(TsGlobals.TS_ELAB_LOG_DIR_PATH)

    # Execute tests
    all_sim_log_files = []
    all_elab_log_files = []

    for test in TsGlobals.TS_TEST_RUN_LIST:
        ts_print(f"Starting test: {test['name']}", color=TsColors.PURPLE)

        # Loop if test shall be run multiple times
        for i in range(args.loop):
            test["seed"] = ts_generate_seed()
            elab_dir = ""

            # Call pre-test hooks
            ts_call_global_hook(TsHooks.PRE_TEST, test["name"], test["seed"], i)
            ts_call_local_hook(
                TsHooks.PRE_TEST_SPECIFIC, test, test["name"], test["seed"], i
            )

            if not args.sim_only:

                #######################################################################################
                # Run elaboration
                #######################################################################################
                elab_log_file, elab_dir = ts_sim_elaborate(test)
                all_elab_log_files.append(elab_log_file)

                if TsGlobals.TS_SIM_CFG.get("fail_fast") and ts_get_cfg(
                    "check_elab_log"
                ):
                    result = sim_check(args, elab_log_file)
                    if result != 0:
                        break

                # If we are run only elaboration and we have multiple tests, run all, don't abort right away!
                if args.elab_only:
                    continue

            #######################################################################################
            # Run simulation
            #######################################################################################
            ts_call_global_hook(TsHooks.PRE_SIM)

            sim_log_file = ts_sim_run(test, elab_dir)
            all_sim_log_files.append(sim_log_file)

            ts_call_local_hook(
                TsHooks.POST_TEST_SPECIFIC, test, test["name"], test["seed"], i
            )
            ts_call_global_hook(TsHooks.POST_TEST, test["name"], test["seed"], i)

            # Check result of single test and abort if there is fail-fast!
            if TsGlobals.TS_SIM_CFG.get("fail_fast"):
                result = sim_check(args, sim_log_file)
                if result != 0:
                    break

    ts_call_global_hook(TsHooks.POST_RUN)

    ret_val = 0
    if not ts_get_cfg("no_check"):

        # Check elab log files
        if ts_get_cfg("check_elab_log"):
            all_sim_log_files.extend(all_elab_log_files)

        # Skip logfile check if list is empty
        if not all_sim_log_files:
            sys.exit(ret_val)

        # Check sim log files
        ts_print("Checking log files", color=TsColors.PURPLE, big=True)
        ret_val = sim_check(args, all_sim_log_files)

        ts_call_global_hook(TsHooks.POST_CHECK)

    sys.exit(ret_val)
