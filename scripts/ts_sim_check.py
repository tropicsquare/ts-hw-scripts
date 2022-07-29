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

import junit_xml
import argcomplete

from internal import *


def sim_check(arguments, log_files):

    args = {
        "exp_junit_logs": False,
        **vars(arguments)
    }

    junit_tests = []

    with TSLogChecker() as checker:

        # Go through the log files provided (multiple arguments) and check results
        for log_file in map(ts_get_curr_dir_rel_path, log_files):

            results = checker.check_single_test(log_file)

            junit_tests.append(generate_junit_test_object(results, log_file, args["exp_junit_logs"]))

    # Create JUnit test collection and export it
    ts = junit_xml.TestSuite("Test results", junit_tests)
    with open(ts_get_root_rel_path(TsGlobals.TS_SIM_JUNIT_SUMMARY_PATH), 'w') as f:
        junit_xml.TestSuite.to_file(f, [ts])

    return checker.cnt_failures

if __name__ == "__main__":

    init_signals_handler()

    # Add arguments
    parser = TsArgumentParser(description="Simulation result check script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_target_arg(parser)
    add_ts_sim_check_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Load config files and check them
    do_sim_config_init(args)
    do_design_config_init(args)

    # Launch checking process
    sim_check(args, args.log_file)
