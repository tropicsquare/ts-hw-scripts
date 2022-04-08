# -*- coding: utf-8 -*-

####################################################################################################
# Handling of script arguments.
#
# TODO: License
####################################################################################################

import argparse
import contextlib
import os

from .ts_hw_global_vars import *
from .ts_hw_common import *


def add_ts_common_args(parser):
    """
    Adds arguments which are common to all scripts (e.g. --verbose)
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Prints most important executed commands and actions. \
                             The more 'v', the more verbose the script.")

    parser.add_argument("-n", "--no-color", action="store_true", default=False,
                        help="Do not use coloured output of the script.")

    parser.add_argument("-c", "--sim-cfg", help="Overrides path of simulation config file (${})".format(
                        os.path.normpath(os.path.join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_CFG_PATH))),
                        default=os.path.normpath(os.path.join(get_repo_root_path(), TsGlobals.TS_SIM_CFG_PATH)))


def add_target_arg(parser):
    """
    Adds compilation/simulation target argument.
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument('target', help='Design target from simulation config file (e.g. ' \
                                       'rtl, gate_min, gate_max)')


def add_ts_sim_compile_args(parser):
    """
    Adds arguments specific to ts_sim_compile.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--clear", action="store_true", default=False,
                        help="Removes all previously compiled sources before compiling (forces \
                             recompilation of all files).")

    parser.add_argument("--clear-logs", action="store_true", default=False,
                        help="Clear log file directories for compilation logs before compiling")

    parser.add_argument("--list-sources", action="store_true",
                        default=False, help="Only list all files that will be compiled, "
                                            "do not run compilation. Files to be compiled "
                                            "are target specific, and they are queried from "
                                            "source list files in simulator config file")

    parser.add_argument("--list-targets", action="store_true",
                        default=False, help="Only list all targets available for compilation, "
                                            "do not run compilation.")

    parser.add_argument("--compile-debug", action="store_true", default=False,
                        help="Forces compilation of all files in debug mode.")

    parser.add_argument("--coverage", action="store_true",
                        help="Forces compilation with coverage instrumentation.")

    parser.add_argument("--add-comp-options", default="",
                         help="Adds extra compile options(switches) to a compile command issued "
                              "to a simulator. Options are added for all compiled files.")

    parser.add_argument("--add-vhdl-comp-options", default="",
                         help="Adds extra compile options to a compile command of a VHDL files.")

    parser.add_argument("--add-verilog-comp-options", default="",
                        help="Adds extra compile options to a compile command of "
                             "Verilog/System Verilog files.")

    parser.add_argument("--exp-tcl-file-dc", default="",
                        help="Exports TCL file with sources for DC shell.")

    parser.add_argument("--exp-tcl-file-vivado", default="",
                        help="Exports TCL file with sources for Vivado.")

    parser.add_argument("--build-dir", help="Overrides default build "
                        "directory (${})".format(
                        os.path.normpath(os.path.join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_BUILD_PATH))),
                        default=os.path.normpath(os.path.join(os.getenv(TsGlobals.TS_REPO_ROOT), TsGlobals.TS_SIM_BUILD_PATH)))

    parser.add_argument("--gui", nargs="?", const="dve", default=None,
                            choices=("dve", "verdi"),
                            help="Compile options may depend on the GUI used for run. Default is '%(const)s'.")

    parser.add_argument("--simulator", help="Overrides used simulator. By default used simulator "
                                            "is given by simulation config file.")


def add_ts_sim_run_args(parser):
    """
    Adds arguments specific to ts_sim_run.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--add-elab-options", default="",
                        help="Adds extra options to elaboration command line.")

    parser.add_argument("--add-sim-options", default="",
                        help="Adds extra options to simulation command line.")

    parser.add_argument("--clear", action="store_true", default=False,
                        help="Removes all previously compiled sources before compiling (forces \
                             recompilation of all files).")

    parser.add_argument("--clear-logs", action="store_true", default=False,
                        help="Clear log file directories for elaboration and simulation logs "
                             "before running elaboration/simulation.")

    parser.add_argument("--coverage", action="store_true", default=False,
                        help="Forces compilation with coverage instrumentation.")

    parser.add_argument("--dump-waves", action="store_true", default=False,
                        help="When set, waves from whole simulation hierarchy are recorded")

    parser.add_argument("--elab-only", action="store_true", default=False,
                        help="Run only elaboration (do not run simulation).")

    parser.add_argument("--sim-only", action="store_true", default=False,
                        help="Run simulation only (do not run elaboration). \
                                Supersedes the '--elab-only' argument.")

    parser.add_argument("--check-elab-log", action="store_true", default=False,
                        help="Check elaboration logs along with simulation logs.")

    # TODO timestamp_log_file

    parser.add_argument("--fail-fast", action="store_true",
                        default=False, help="When running multiple tests, if a test fail, "
                                            "finish and do not run next tests.")

    parser.add_argument("--gui", nargs="?", const="dve", default=None,
                            choices=("dve", "verdi"),
                            help="Launch simulation in GUI mode. Default is '%(const)s'.")

    parser.add_argument("--license-wait", action="store_true", default=False,
                        help="When set, simulator waits for a license if it is not available.")

    parser.add_argument("--list-tests", action="store_true", default=False,
                        help="Only print list of available tests, do not run simulation.")

    parser.add_argument("--loop", type=int, help="Repeat each test N times.", default=1)

    parser.add_argument("--no-check", action="store_true", default=False,
                        help="Do not call 'ts_sim_check.py' after the run of the test.")

    parser.add_argument("--no-sim-out", action="store_true",
                        default=False, help="Disable simulator output from elaboration and "
                                            "simulation to command line. (Log file is still "
                                            "recorded).")

    parser.add_argument("--recompile", action="store_true", default=False,
                        help="Force recompilation of the target before running simulation.")

    parser.add_argument("--seed", type=int, default=argparse.SUPPRESS, help="Seed for randomization.")

    parser.add_argument("--session-file", default=argparse.SUPPRESS,
                        help="Loads session file for GUI viewer.")

    parser.add_argument("--do-file", default=argparse.SUPPRESS,
                        help="Loads do file for simulator.")

    parser.add_argument("--sim-verbosity", default="info",
                        choices=("debug", "info", "warning", "error"),
                        help="Specifies simulation verbosity, Default is '%(default)s'.")

    parser.add_argument("--exp-junit-logs",
                        help="Export log files into JUnit output for Gitlab",
                        action="store_true", default=False)

    parser.add_argument("test_name", help="Name of the test to execute.", nargs="*")


def add_ts_sim_regress_args(parser):
    """
    Adds arguments specific to ts_sim_run.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--license-wait", action="store_true", default=False,
                        help="When set, simulator waits for a license if it is not available.")

    parser.add_argument("--recompile", action="store_true", default=False,
                        help="Force recompilation of the target before running simulation.")

    parser.add_argument("--regress-jobs", default=1, type=int,
                        help="Number of parallel jobs to launch.")

    parser.add_argument("--sim-verbosity", default="info",
                        choices=("debug", "info", "warning", "error"),
                        help="Specifies simulation verbosity, Default is '%(default)s'.")

    parser.add_argument("--exp-junit-logs", 
                        help="Export log files into JUnit output for Gitlab",
                        action="store_true", default=False)

    parser.add_argument("--do-file", default=argparse.SUPPRESS,
                        help="Loads do file for simulator.")

    parser.add_argument("test_name", help="Name of the test/test group to execute.", nargs="*")

    parser.add_argument("--check-elab-log", action="store_true", default=False,
                        help="Check elaboration logs along with simulation logs.")


def add_ts_sim_check_args(parser):
    """
    Adds arguments specific to ts_sim_check.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--exp-junit-logs",
                        help="Export log files into JUnit output for Gitlab",
                        action="store_true", default=False)

    parser.add_argument("log_file", help="Path to log file. If it is relative, then it is "
                                         "interpreted as relative to TS_REPO_ROOT. If it is "
                                         "absolute, then it is interpreted as absolute path",
                        nargs="+")


def add_ts_sim_coverage_args(parser):
    """
    Adds arguments specific to ts_sim_coverage.py
    :param parser: Argparse parser to which arguments shall be added
    """

    parser.add_argument("test", help="Test(s) whose database is processed.", nargs="*")

    parser.add_argument("--clean", action="store_true", default=False,
                        help=f"Remove {ts_get_root_rel_path(TsGlobals.TS_COVERAGE_DIR_PATH)}.")

    parser.add_argument("--clear", action="store_true", default=False,
                        help="Removes output database if previously created.")

    parser.add_argument("--gui", action="store_true", default=False,
                            help="Display results in GUI.")

    parser.add_argument("--no-report", action="store_true", default=False,
                        help="Do not generate report upon database merge")

    parser.add_argument("--no-sim-out", action="store_true", default=False,
                        help="Disable output from merge.")

    parser.add_argument("-o", "--output", default=argparse.SUPPRESS,
                        help="Result database.")

