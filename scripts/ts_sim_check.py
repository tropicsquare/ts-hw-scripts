#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square Simulation result check script
#
# TODO: License
####################################################################################################

__author__ = "Ondrej Ille"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Ondrej Ille"

import logging
import os
import sys
import junit_xml
import argcomplete

from internal import *


if __name__ == "__main__":

    init_signals_handler()
    
    # Add arguments
    parser = argparse.ArgumentParser(description="Simulation result check script")
    add_ts_common_args(parser)
    add_target_arg(parser)
    add_ts_sim_check_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Load config file and check it
    do_config_init(args)

    # Print test results header
    ts_info(TsInfoCode.INFO_CMN_16)
    print_test_result_header()

    # Go through the log files provided (multiple arguments) and check results
    failed_cnt = 0
    total_run_time = 0.0
    total_err = 0
    total_warn = 0
    total_ign_err = 0
    total_ign_warn = 0

    junit_tests = []

    for sim_log_file_path in args.log_file:

        # Target is not passed to ts_sim_check.py. Parse it out of log file name
        #filename = os.path.basename(sim_log_file_path)
        #ts_set_cfg("target", filename.split("_")[1])

        sim_log_file_path = ts_get_curr_dir_rel_path(sim_log_file_path)
        results = check_single_test(sim_log_file_path)
        print_test_result(results)
        junit_tests.append(generate_junit_test_object(results, sim_log_file_path, args.exp_junit_logs))

        if not results["result"]:
            failed_cnt += 1
        total_run_time += results["run_time"]
        total_err += len(results["errors"])
        total_warn += len(results["warnings"])
        total_ign_err += len(results["ignored_errors"])
        total_ign_warn += len(results["ignored_warnings"])

    # Create JUnit test collection and export it
    ts = junit_xml.TestSuite("Test results", junit_tests)
    with open(ts_get_root_rel_path(TsGlobals.TS_SIM_JUNIT_SUMMARY_PATH), 'w') as f:
        junit_xml.TestSuite.to_file(f, [ts])

    # Print summary
    print_test_summary(total_run_time, total_err, total_warn, total_ign_err, total_ign_warn,
                       failed_cnt, len(args.log_file))

    sys.exit(failed_cnt)

