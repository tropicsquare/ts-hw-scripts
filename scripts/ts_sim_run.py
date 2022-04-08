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
import os
import argcomplete

from internal import *
from ts_sim_check import sim_check
from ts_sim_compile import sim_compile


if __name__ == "__main__":

    init_signals_handler()
    
    # Add script arguments
    parser = argparse.ArgumentParser(description="Digital simulation script")
    add_ts_common_args(parser)
    add_target_arg(parser)
    add_ts_sim_run_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    TsGlobals.TS_SIM_CFG_PATH = args.sim_cfg
    ts_configure_logging(args)

    # Load config file, merge with args and check configuration
    do_config_init(args)

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
        print("Tests available:")
        print_test_list(TsGlobals.TS_TEST_LIST, False)
        sys.exit(0)

    # Check that no test is given as a special option
    if not args.test_name:
        ts_throw_error(TsErrCode.ERR_SLF_15)

    # Find tests to be executed
    if len(get_tests_to_run(args.test_name)) == 0:
        ts_throw_error(TsErrCode.ERR_SLF_14, str(args.test_name))

    # Print tests to be executed
    ts_info(TsInfoCode.INFO_CMN_13)
    print_test_list(TsGlobals.TS_TEST_RUN_LIST, False)
    print_test_iterations()

    ts_call_global_hook(TsHooks.PRE_RUN)

    # Clear log directories if user wants
    if ts_get_cfg("clear_logs"):
        shutil.rmtree(ts_get_root_rel_path(TsGlobals.TS_ELAB_LOG_DIR_PATH), ignore_errors=True)
        shutil.rmtree(ts_get_root_rel_path(TsGlobals.TS_SIM_LOG_DIR_PATH), ignore_errors=True)

    # Create sim_logs, elab_logs directories
    ts_debug("Create 'sim_logs' directory (if it does not exist)")
    create_sim_sub_dir(TsGlobals.TS_SIM_LOG_DIR_PATH)
    ts_debug("Create elaboration log directory")
    create_sim_sub_dir(TsGlobals.TS_ELAB_LOG_DIR_PATH)

    # Execute tests
    all_sim_log_files = []
    all_elab_log_files = []

    for test in TsGlobals.TS_TEST_RUN_LIST:
        ts_big_info(TsInfoCode.INFO_CMN_14, test["name"])

        # Loop if test shall be run multiple times
        for i in range(args.loop):
            test["seed"] = ts_generate_seed()

            # Call pre-test hooks
            ts_call_global_hook(TsHooks.PRE_TEST, test["name"], test["seed"], i)
            ts_call_local_hook(TsHooks.PRE_TEST_SPECIFIC, test, test["name"], test["seed"], i)

            if not args.sim_only:

                #######################################################################################
                # Run elaboration
                #######################################################################################
                elab_log_file = ts_sim_elaborate(test)
                all_elab_log_files.append(elab_log_file)

                if TsGlobals.TS_SIM_CFG.get("fail_fast") and ts_get_cfg("check_elab_log"):
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
            
            sim_log_file = ts_sim_run(test)
            all_sim_log_files.append(sim_log_file)

            ts_call_local_hook(TsHooks.POST_TEST_SPECIFIC, test, test["name"], test["seed"], i)
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
        ts_big_info(TsInfoCode.INFO_GENERIC, "{}".format("Checking log files:"))
        ret_val = sim_check(args, all_sim_log_files)
        
        ts_call_global_hook(TsHooks.POST_CHECK)

    sys.exit(ret_val)

