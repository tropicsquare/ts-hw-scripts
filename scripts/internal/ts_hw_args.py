# -*- coding: utf-8 -*-

####################################################################################################
# Handling of script arguments.
#
# TODO: License
####################################################################################################

from os.path import join, normpath
from textwrap import dedent
from argparse import ArgumentParser, RawTextHelpFormatter, SUPPRESS

from .__version__ import __version__
from .ts_hw_global_vars import *
from .ts_hw_common import *


__norm_join = lambda *paths: normpath(join(*paths))


class TsArgumentParser(ArgumentParser):

    def __init__(self, description):
        super().__init__(description=description,
                        formatter_class=RawTextHelpFormatter)


def add_ts_common_args(parser):
    """
    Adds arguments which are common to all scripts (e.g. --verbose)
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Prints most important executed commands and actions. "
                             "The more 'v', the more verbose the script.")

    parser.add_argument("-n", "--no-color", action="store_true", default=False,
                        help="Do not use coloured output of the script.")

    parser.add_argument("-c", "--sim-cfg",
                        default=ts_get_root_rel_path(TsGlobals.TS_SIM_CFG_PATH),
                        help="Overrides simulation config file, default is "
                            f"${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_CFG_PATH)}")


def add_target_arg(parser):
    """
    Adds compilation/simulation target argument.
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("target",
                        help="Design target from simulation config file "
                            "(e.g. rtl, gate_min, gate_max)")


def add_ts_sim_compile_args(parser):
    """
    Adds arguments specific to ts_sim_compile.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--clear", action="store_true", default=False,
                        help="Removes all previously compiled sources before compiling "
                            "(forces recompilation of all files).")

    parser.add_argument("--clear-logs", action="store_true", default=False,
                        help="Clear log file directories for compilation logs before compiling")

    parser.add_argument("--list-sources", action="store_true", default=False,
                        help="Only list all files that will be compiled, do not run compilation. "
                            "\nFiles to be compiled are target specific, and they are queried from "
                            "source list files in simulator config file")

    parser.add_argument("--list-targets", action="store_true", default=False,
                        help="Only list all targets available for compilation, "
                            "do not run compilation.")

    parser.add_argument("--compile-debug", action="store_true", default=False,
                        help="Forces compilation of all files in debug mode.")

    parser.add_argument("--coverage", action="store_true",
                        help="Forces compilation with coverage instrumentation.")

    parser.add_argument("--add-comp-options", default="",
                         help="Adds extra compile options (switches) to a compile command issued "
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

    parser.add_argument("--build-dir", default=SUPPRESS,
                        help="Overrides default build directory, default is "
                        f"${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_BUILD_PATH)}")

    parser.add_argument("--gui", nargs="?", const="dve", default=None, choices=("dve", "verdi"),
                        help="Compile options may depend on the GUI used for run. Default is '%(const)s'.")

    parser.add_argument("--simulator",
                        help="Overrides used simulator. "
                            "By default simulator is given by simulation config file.")


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
                        help="Removes all previously compiled sources before compiling "
                            "(forces recompilation of all files).")

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
                        help="Run simulation only (do not run elaboration). "
                            "Supersedes the '--elab-only' argument.")

    parser.add_argument("--check-elab-log", action="store_true", default=False,
                        help="Check elaboration logs along with simulation logs.")

    parser.add_argument("--fail-fast", action="store_true", default=False,
                        help="When running multiple tests, if a test fail, "
                            "finish and do not run next tests.")

    parser.add_argument("--gui", nargs="?", const="dve", default=None,
                        choices=("dve", "verdi"),
                        help="Launch simulation in GUI mode. Default is '%(const)s'.")

    parser.add_argument("--license-wait", action="store_true", default=False,
                        help="When set, simulator waits for a license if it is not available.")

    parser.add_argument("--list-tests", action="store_true", default=False,
                        help="Only print list of available tests, do not run simulation.")

    parser.add_argument("--loop", type=int, default=1,
                        help="Repeat each test N times.")

    parser.add_argument("--no-check", action="store_true", default=False,
                        help="Do not call 'ts_sim_check.py' after the run of the test.")

    parser.add_argument("--no-sim-out", action="store_true", default=False,
                        help="Disable simulator output from elaboration and simulation "
                            "to command line (Log file is stil recorded).")

    parser.add_argument("--recompile", action="store_true", default=False,
                        help="Force recompilation of the target before running simulation.")

    parser.add_argument("--seed", type=int, default=SUPPRESS,
                        help="Seed for randomization.")

    parser.add_argument("--session-file", default=SUPPRESS,
                        help="Loads session file for GUI viewer.")

    parser.add_argument("--do-file", default=SUPPRESS,
                        help="Loads do file for simulator.")

    parser.add_argument("--sim-verbosity", default="info",
                        choices=("debug", "info", "warning", "error"),
                        help="Specifies simulation verbosity, Default is '%(default)s'.")

    parser.add_argument("--exp-junit-logs", action="store_true", default=False,
                        help="Export log files into JUnit output for Gitlab")

    parser.add_argument("test_name", nargs="*",
                        help="Name of the test to execute.")


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

    parser.add_argument("--exp-junit-logs", action="store_true", default=False,
                        help="Export log files into JUnit output for Gitlab")

    parser.add_argument("--do-file", default=SUPPRESS,
                        help="Loads do file for simulator.")

    parser.add_argument("test_name", nargs="*",
                        help="Name of the test/test group to execute.")

    parser.add_argument("--check-elab-log", action="store_true", default=False,
                        help="Check elaboration logs along with simulation logs.")


def add_ts_sim_check_args(parser):
    """
    Adds arguments specific to ts_sim_check.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--exp-junit-logs",
                        action="store_true", default=False,
                        help="Export log files into JUnit output for Gitlab")

    parser.add_argument("log_file", nargs="+",
                        help=dedent(f"""\
                        Path to log files.
                        Format is either:
                        - path relative to ${TsGlobals.TS_REPO_ROOT}
                        - absolute path"""))


def add_ts_sim_coverage_args(parser):
    """
    Adds arguments specific to ts_sim_coverage.py
    :param parser: Argparse parser to which arguments shall be added
    """

    parser.add_argument("test", nargs="*",
                        help=dedent(f"""\
                        Tests whose database is processed.
                        Format is either:
                        - test name
                        - path relative to ${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_COVERAGE_DIR_PATH)}
                        - absolute path"""))

    parser.add_argument("--clean", action="store_true", default=False,
                        help=f"Remove ${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_COVERAGE_DIR_PATH)}")

    parser.add_argument("--clear", action="store_true", default=False,
                        help="Remove output database if previously created.")

    parser.add_argument("-e", "--elfile",
                        help=f"Use exclusion file (location relative to ${TsGlobals.TS_REPO_ROOT})")

    parser.add_argument("--gui", action="store_true", default=False,
                         help="Display results in GUI.")

    parser.add_argument("--no-report", action="store_true", default=False,
                        help="Do not generate report upon database merge")

    parser.add_argument("--no-sim-out", action="store_true", default=False,
                        help="Disable output from merge.")

    parser.add_argument("-o", "--output", default=SUPPRESS,
                        help=dedent(f"""\
                        Result database.
                        Format is either:
                        - database name
                        - path relative to ${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_COVERAGE_DIR_PATH)}
                        - absolute path"""))

