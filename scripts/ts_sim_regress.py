#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square Parallel regression script for digital simulations
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
from concurrent.futures import ProcessPoolExecutor, wait
from copy import deepcopy

import argcomplete
from internal.ts_hw_args import (
    TsArgumentParser,
    add_cfg_files_arg,
    add_target_arg,
    add_ts_common_args,
    add_ts_sim_regress_args,
)
from internal.ts_hw_cfg_parser import (
    do_design_config_init,
    do_sim_config_init,
    fill_default_config_regress_values,
)
from internal.ts_hw_common import (
    check_target,
    create_sim_sub_dir,
    get_regression_dest_dir_name,
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
from internal.ts_hw_simulator_ifc import ts_sim_elaborate
from internal.ts_hw_test_list_files import get_test_list, get_tests_to_run, load_tests
from ts_sim_check import sim_check
from ts_sim_compile import sim_compile
from ts_sim_run import ts_sim_run


def elaborate_regression_test(test, loop_index):
    """
    Elaborate single test.
    """
    ts_print(
        f"Starting test: {test['name']}-{loop_index}", color=TsColors.PURPLE, big=True
    )

    test["seed"] = ts_generate_seed()

    # Call pre-test hooks
    ts_call_global_hook(TsHooks.PRE_TEST, test["name"], test["seed"], loop_index)
    ts_call_local_hook(
        TsHooks.PRE_TEST_SPECIFIC, test, test["name"], test["seed"], loop_index
    )

    #######################################################################################
    # Run elaboration
    #######################################################################################
    return ts_sim_elaborate(test)


def run_regression_test(test, loop_index, elab_dir):
    """
    Run single test.
    """
    #######################################################################################
    # Run simulation
    #######################################################################################
    ts_call_global_hook(TsHooks.PRE_SIM)

    sim_log_file = ts_sim_run(test, elab_dir)

    # Call post-test hooks
    ts_call_local_hook(
        TsHooks.POST_TEST_SPECIFIC, test, test["name"], test["seed"], loop_index
    )
    ts_call_global_hook(TsHooks.POST_TEST, test["name"], test["seed"], loop_index)

    return sim_log_file


if __name__ == "__main__":

    init_signals_handler()

    # Add script arguments
    parser = TsArgumentParser(description="Digital regression script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_target_arg(parser)
    add_ts_sim_regress_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    TsGlobals.TS_SIM_CFG_PATH = args.sim_cfg
    ts_configure_logging(args)

    # Load config file, merge with args and check configuration
    do_sim_config_init(args)
    do_design_config_init(args)

    # Fill default config values for command line options which are not available
    # in ts_sim_regress.py
    fill_default_config_regress_values(ts_get_cfg())

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

    # Check that no test is given as a special option
    if not args.test_name:
        ts_throw_error(TsErrCode.ERR_SLF_15)

    # Find tests to be executed
    if len(get_tests_to_run(args.test_name)) == 0:
        ts_throw_error(TsErrCode.ERR_SLF_14, str(args.test_name))

    # Fill regression iterations if not set for each test
    for test in TsGlobals.TS_TEST_RUN_LIST:
        test.setdefault("regress_loops", 1)

    # Print tests to be executed
    ts_info(TsInfoCode.INFO_CMN_13, get_test_list(TsGlobals.TS_TEST_RUN_LIST, get_repeat=True))
    ts_info(TsInfoCode.GENERIC, "Number of parallel jobs: {ts_get_cfg('regress_jobs')}")

    ts_call_global_hook(TsHooks.PRE_RUN)

    # Clear log directories always. This makes sure that only logs from this regression
    # are backed up.
    shutil.rmtree(ts_get_root_rel_path(TsGlobals.TS_ELAB_LOG_DIR_PATH), ignore_errors=True)
    shutil.rmtree(ts_get_root_rel_path(TsGlobals.TS_SIM_LOG_DIR_PATH), ignore_errors=True)

    # Create sim_logs, elab_logs directories
    ts_debug("Create 'sim_logs' directory (if it does not exist)")
    create_sim_sub_dir(TsGlobals.TS_SIM_LOG_DIR_PATH)
    ts_debug("Create elaboration log directory")
    create_sim_sub_dir(TsGlobals.TS_ELAB_LOG_DIR_PATH)

    ###############################################################################################
    # Execute tests
    ###############################################################################################

    all_sim_log_files = []
    all_elab_log_files = []

    futures = []

    with ProcessPoolExecutor(ts_get_cfg("regress_jobs")) as executor:
        for test in TsGlobals.TS_TEST_RUN_LIST:
            for i in range(test["regress_loops"]):
                _test = deepcopy(test)
                # Elaborate each test one by one - blocking
                elab_log_file, elab_dir = elaborate_regression_test(_test, i)
                all_elab_log_files.append(elab_log_file)
                # Enqueue run job in thread pool - non-blocking
                futures.append(executor.submit(run_regression_test, _test, i, elab_dir))
        # Wait until all jobs are finished
        wait(futures)

    all_sim_log_files = [future.result() for future in futures]

    ts_call_global_hook(TsHooks.POST_RUN)

    ###############################################################################################
    # Check results.
    ###############################################################################################

    ret_val = 0
    if not ts_get_cfg("no_check"):

        # Check elab log files
        if ts_get_cfg("check_elab_log"):
            all_sim_log_files.extend(all_elab_log_files)

        # Check sim log files
        ts_info(TsInfoCode.GENERIC, "Checking log files:")
        ret_val = sim_check(args, all_sim_log_files)

        ts_call_global_hook(TsHooks.POST_CHECK)

    ###############################################################################################
    # Backup regression logs
    ###############################################################################################

    reg_dir = get_regression_dest_dir_name()
    sim_logs_dir = ts_get_root_rel_path(TsGlobals.TS_SIM_LOG_DIR_PATH)
    elab_logs_dir = ts_get_root_rel_path(TsGlobals.TS_ELAB_LOG_DIR_PATH)

    ts_info(TsInfoCode.GENERIC, f"Copying regression logs to {reg_dir}")

    os.mkdir(reg_dir)
    shutil.copytree(sim_logs_dir, os.path.join(reg_dir, os.path.basename(sim_logs_dir)))
    shutil.copytree(elab_logs_dir, os.path.join(reg_dir, os.path.basename(elab_logs_dir)))

    sys.exit(ret_val)

