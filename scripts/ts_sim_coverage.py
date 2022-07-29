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
import pickle
import shutil
import argcomplete

from internal import *


COVERAGE_OUTPUT_DIR = ts_get_root_rel_path(TsGlobals.TS_COVERAGE_DIR_PATH)
DEFAULT_OUTPUT_DB   = "coverage_merge"


def __merge_databases(args):
    """
    Merge input databases
    """

    # - Create command line
    command = ["urg -full64"]

    # - Manage reporting
    if args["no_report"]:
        command.append("-noreport")
        ts_debug("Coverage databases will be merged without report.")

    # - Add simulation databases
    input_dbs = set()
    if args["test"]:
        # Take specified databases
        for test in args["test"]:
            # test can be either:
            #   - name of the database, e.g. sim_rtl_test_525447
            #   - path relative to TS_SIM_BUILD_PATH, e.g. sim_rtl_test_525447/simv.vdb
            #   - absolute path, e.g. /projects/tropic01/sim/build/sim_rtl_test_525447/simv.vdb
            if not test.endswith("simv.vdb"):
                input_db = ts_get_root_rel_path(TsGlobals.TS_SIM_BUILD_PATH, test, "simv.vdb")
            else:
                input_db = ts_get_root_rel_path(TsGlobals.TS_SIM_BUILD_PATH, test)
            ts_debug(f"Checking existence of '{input_db}'")
            if not os.path.exists(input_db):
                ts_throw_error(TsErrCode.GENERIC, f"Input database '{input_db}' does not exist! "
                                        "Make sure you ran the simulation with the '--coverage' option.")
            ts_debug("OK")
            input_dbs.add(input_db)
    else:
        # Else take all databases available in build directory
        build_dir = ts_get_root_rel_path(TsGlobals.TS_SIM_BUILD_PATH)
        if not os.path.isdir(build_dir):
            ts_throw_error(TsErrCode.GENERIC, f"Build directory '{build_dir}' does not exist! "
                                        "Make sure to run some simulation before launching coverage tool.")
        for dir_entry in os.scandir(build_dir):
            if dir_entry.is_dir() and dir_entry.name.startswith("sim"):
                sim_db = os.path.join(dir_entry.path, "simv.vdb")
                if os.path.isdir(sim_db):
                    ts_debug(f"Adding simulation database: '{sim_db}'")
                    input_dbs.add(sim_db)
        if not input_dbs:
            ts_throw_error(TsErrCode.GENERIC, "Could not find any database to merge!")

    # Add elaboration coverage databases associated to simulation databases
    for sim_db in input_dbs.copy():
        with open(os.path.join(os.path.dirname(sim_db),
                                "_ts_flow_reference_elaboration_directory"), "rb") as fd:
            elab_db = os.path.join(pickle.load(fd), "simv.vdb")
            if elab_db not in input_dbs:
                ts_debug(f"Adding elaboration database: '{elab_db}'")
                input_dbs.add(elab_db)

    for input_db in input_dbs:
        command.append(f"-dir {input_db}")

    # - Exclusion file
    if args["elfile"]:
        elfile = ts_get_root_rel_path(args["elfile"])
        if not os.path.isfile(elfile):
            ts_throw_error(TsErrCode.GENERIC, f"Exclusion file '{elfile}' does not exist.")
        ts_info(TsInfoCode.GENERIC, f"Using exclusion file '{elfile}'")
        command.append(f"-elfile {elfile}")

    # - Output database management
    output_db = args.get("output", DEFAULT_OUTPUT_DB)

    # output arg can be either:
    #   - name of the database, e.g. example_db
    #   - path relative to COVERAGE_OUTPUT_DIR, e.g. example_db.vdb
    #   - absolute path, e.g. /projects/tropic01/sim/coverage_output/example_db.vdb
    if not output_db.endswith(".vdb"):
        output_db += ".vdb"
    output_db = os.path.join(COVERAGE_OUTPUT_DIR, output_db)
    if args["clear"]:
        ts_debug(f"Removing directory '{output_db}'")
        shutil.rmtree(output_db, ignore_errors=True)
    ts_info(TsInfoCode.GENERIC, f"Checking absence of '{output_db}'")
    if os.path.isdir(output_db):
        ts_throw_error(TsErrCode.GENERIC, f"Output database '{output_db}' already exists! "
                                                "Activate the '--clear' option to remove it.")
    ts_debug("OK")
    command.append(f"-dbname {output_db}")

    # - Format command
    command = " ".join(command)
    ts_info(TsInfoCode.GENERIC, command)

    # - Run coverage
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


def __show_output_database(args):
    """
    Display output database in GUI
    """

    # - Output database management
    output_db = args.get("output", DEFAULT_OUTPUT_DB)

    # - Check output database exists
    # output arg can be either:
    #   - name of the database, e.g. example_db
    #   - path relative to COVERAGE_OUTPUT_DIR, e.g. example_db.vdb
    #   - absolute path, e.g. /projects/tropic01/sim/coverage_output/example_db.vdb
    ts_debug(f"Checking existence of '{output_db}'")
    if not output_db.endswith(".vdb"):
        output_db += ".vdb"
    output_db = os.path.join(COVERAGE_OUTPUT_DIR, output_db)
    ts_info(TsInfoCode.GENERIC, f"Testing existence of '{output_db}'")
    if not os.path.isdir(output_db):
        ts_throw_error(TsErrCode.GENERIC, f"Database '{output_db}' does not exist!")
    ts_debug("OK")

    # - Create command
    command = f"$VCS_HOME/gui/dve/bin/dve -full64 -ucliplatform=linux64 -cov -dir {output_db}"
    ts_info(TsInfoCode.GENERIC, os.path.expandvars(command))

    # - Run GUI command
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
        **vars(arguments)
    }

    # Remove coverage output directory
    if args["clean"]:
        ts_debug(f"Removing {COVERAGE_OUTPUT_DIR}")
        exit_code = shutil.rmtree(COVERAGE_OUTPUT_DIR, ignore_errors=True)

    # Show output database
    elif args["gui"]:
        exit_code = __show_output_database(args)

    # Merge input databases
    else:
        exit_code = __merge_databases(args)

    return exit_code


if __name__ == "__main__":

    init_signals_handler()

    # Add script arguments
    parser = TsArgumentParser(description="Coverage script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_ts_sim_coverage_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    TsGlobals.TS_SIM_CFG_PATH = args.sim_cfg
    ts_configure_logging(args)

    # Load config file, merge with args and check configuration
    do_sim_config_init(args, skip_check=True)

    # Launch compilation
    sys.exit(sim_coverage(args))

