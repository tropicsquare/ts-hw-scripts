#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square coverage script for digital simulations
#
# TODO: License
####################################################################################################

__author__ = "Henri LHote"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Henri LHote"

import os
import sys
import time
import shutil
import argcomplete

from internal import *


COVERAGE_OUTPUT_DIR = ts_get_root_rel_path(TsGlobals.TS_COVERAGE_DIR_PATH)


def __merge_databases(args):
    """
    Merge input databases
    """

    # Create command line
    command = ["urg -full64"]

    # Manage reporting
    if args["no_report"]:
        command.append("-noreport")
        ts_debug("Coverage database(s) will be merged without report.")

    # Check databases
    for test in args["test"]:
        input_db = ts_get_root_rel_path(os.path.join(TsGlobals.TS_SIM_BUILD_PATH, f"{test}/simv.vdb"))
        ts_debug(f"Checking existence of '{input_db}'")
        if not os.path.exists(input_db):
            ts_throw_error(TsErrCode.ERR_GENERIC, f"Input database '{input_db}' does not exist! "
                                    "Make sure you ran the simulation with the '--coverage' option.")
        ts_debug("OK")
        command.append(f"-dir {input_db}")

    # Check output directory
    if args["output"]:
        output_db = os.path.join(COVERAGE_OUTPUT_DIR, f"{args['output']}.vdb")
        if args["clear"]:
            ts_debug(f"Removing directory '{output_db}'")
            shutil.rmtree(output_db, ignore_errors=True)
        ts_debug(f"Checking absence of '{output_db}'")
        if os.path.exists(output_db):
            ts_throw_error(TsErrCode.ERR_GENERIC, f"Output database '{output_db}' already exists! "
                                                    "Activate the '--clear' option to remove it.")
        ts_debug("OK")
        command.append(f"-dbname {args['output']}")

    # Format command
    command = " ".join(command)
    ts_info(TsInfoCode.INFO_GENERIC, command)

    # Run coverage
    os.makedirs(COVERAGE_OUTPUT_DIR, exist_ok=True)
    run_time = time.time()
    merge_exit_code = exec_cmd_in_dir(
        directory=COVERAGE_OUTPUT_DIR,
        command=command,
        no_std_out=ts_get_cfg("no_sim_out"),
        no_std_err=ts_get_cfg("no_sim_out")
    )
    run_time = time.time() - run_time
    ts_debug(f"Coverage merge runtime: {run_time:0.3e} second(s).")
    ts_debug(f"Exit code: {merge_exit_code}.")
    return merge_exit_code


def __show_output_database(output_db):
    """
    Display output database in GUI
    """

    # Check output database exists
    output_db = os.path.join(COVERAGE_OUTPUT_DIR, f"{output_db}.vdb")
    ts_debug(f"Checking existence of '{output_db}'")
    if not os.path.exists(output_db):
        ts_throw_error(TsErrCode.ERR_GENERIC, f"Database '{output_db}' does not exist!")
    ts_debug("OK")

    # Create command
    command = f"$VCS_HOME/gui/dve/bin/dve -full64 -ucliplatform=linux64 -cov -dir {output_db}"
    ts_info(TsInfoCode.INFO_GENERIC, os.path.expandvars(command))

    # Run GUI command
    return exec_cmd_in_dir(
        directory=COVERAGE_OUTPUT_DIR,
        command=command,
        no_std_out=ts_get_cfg("no_sim_out"),
        no_std_err=ts_get_cfg("no_sim_out")
    )


def sim_coverage(arguments):

    args = {
        "test": [],
        "clean": False,
        "clear": False,
        "gui": False,
        "no_report": False,
        "no_sim_out": False,
        "output": "",
        **vars(arguments)
    }

    exit_code = "__invalid__"

    # Remove coverage output directory
    if args["clean"]:
        ts_debug(f"Removing {COVERAGE_OUTPUT_DIR}")
        exit_code = shutil.rmtree(COVERAGE_OUTPUT_DIR, ignore_errors=True)

    # Merge input databases
    if args["test"]:
        exit_code = __merge_databases(args)
        if not exit_code and args["gui"] and args["output"]:
            __show_output_database(args["output"])
    # Show output database
    elif args["gui"] and args["output"]:
        exit_code = __show_output_database(args["output"])

    # Throw an error if nothing can be done with input configuration
    if exit_code == "__invalid__":
        ts_throw_error(TsErrCode.ERR_GENERIC, "Invalid arguments! "
                                        "At least specify test(s) to process "
                                        "or the '--gui' option and the output database to show.")

    return exit_code


if __name__ == "__main__":

    init_signals_handler()

    # Add script arguments
    parser = argparse.ArgumentParser(description="Coverage script")
    add_ts_common_args(parser)
    add_ts_sim_coverage_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    TsGlobals.TS_SIM_CFG_PATH = args.sim_cfg
    ts_configure_logging(args)

    # Load config file, merge with args and check configuration
    do_config_init(args, skip_check=True)

    # Launch compilation
    sys.exit(sim_coverage(args))

