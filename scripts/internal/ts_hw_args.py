# -*- coding: utf-8 -*-

####################################################################################################
# Handling of script arguments.
#
# TODO: License
####################################################################################################

import argparse
import contextlib
import os
from typing import NamedTuple

from .ts_hw_global_vars import *
from .ts_hw_common import *


def add_ts_common_args(parser):
    """
    Adds arguments which are common to all scripts (e.g. --verbose)
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="Prints most important commands and actions executed by a script and \
                             underlying compiler/simulator.")
    TsGlobals.TS_CMN_ARGS.append(CommonArg("--verbose"))

    parser.add_argument("-vv", "--very-verbose", action="store_true",
                        default=False, help="Prints almost all commands and actions exectued by a \
                                            script and underlying compiler/simulator.")
    TsGlobals.TS_CMN_ARGS.append(CommonArg("--very-verbose"))

    parser.add_argument("-d", "--script-debug", action="store_true",
                        default=False, help="Run script in debug mode (displays extra information)")
    TsGlobals.TS_CMN_ARGS.append(CommonArg("--script-debug"))

    parser.add_argument("-n", "--no-color", action="store_true", default=False,
                        help="Do not use coloured output of the script.")
    TsGlobals.TS_CMN_ARGS.append(CommonArg("--no-color"))

    parser.add_argument("-c", "--sim-cfg", help="Overrides path of simulation config file (${})".format(
                        os.path.normpath(os.path.join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_CFG_PATH))),
                        default=os.path.normpath(os.path.join(get_repo_root_path(), TsGlobals.TS_SIM_CFG_PATH)))
    TsGlobals.TS_CMN_ARGS.append(CommonArg("--sim-cfg", take_value=True))


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
    TsGlobals.TS_RUN_TO_COMPILE_ARGS.append(CommonArg("--clear"))

    parser.add_argument("--clear-logs", action="store_true", default=False,
                        help="Clear log file directories for elaboration and simulation logs "
                             "before running elaboration/simulation.")
    TsGlobals.TS_RUN_TO_COMPILE_ARGS.append(CommonArg("--clear-logs"))

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
    TsGlobals.TS_RUN_TO_COMPILE_ARGS.append(CommonArg("--gui", take_value=True))

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

    parser.add_argument("--sim-verbosity", default="info",
                        choices=("debug", "info", "warning", "error"),
                        help="Specifies simulation verbosity, Default is '%(default)s'.")

    parser.add_argument("--exp-junit-logs",
                        help="Export log files into JUnit output for Gitlab",
                        action="store_true", default=False)
    TsGlobals.TS_RUN_TO_CHECK_ARGS.append(CommonArg("--exp-junit-logs"))

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
    TsGlobals.TS_RUN_TO_CHECK_ARGS.append(CommonArg("--exp-junit-logs"))

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


class CommonArg(NamedTuple):
    """
    Practical class to share common arguments
    """

    name: str
    dest: str = ""
    take_value: bool = False

    @property
    def argname(self):
        if self.dest:
            return self.dest
        return self.name.lstrip('-').replace('-', '_')


def __get_args(global_list, args):
    ret_val = []
    # Passes arguments which were added to global list of common arguments.
    for arg in global_list:
        with contextlib.suppress(AttributeError):
            arg_val = getattr(args, arg.argname)
            # if arg is set, share it
            if arg_val:
                ret_val.append(arg.name)
                # in addition, take value associated to arg if required
                if arg.take_value:
                    ret_val.append(arg_val)
    return ret_val


def get_common_args(args):
    """
    Take common arguments/configuration from one script and form a command line for another.
    This-way another script can pass common arguments to other script.
    :param args: Parsed arguments object
    """
    return __get_args(TsGlobals.TS_CMN_ARGS, args)


def get_ts_sim_check_args(args):
    """
    Take arguments which should be passed from ts_sim_run/regress to ts_sim_check and
    format them to ts_sim_check.py command line.
    :param args: Parsed arguments object
    """
    return __get_args(TsGlobals.TS_RUN_TO_CHECK_ARGS, args)


def get_ts_sim_compile_args(args):
    """
    Take arguments which should be passed from ts_sim_run/regress to ts_sim_compile and
    format them to ts_sim_compile.py command line.
    :param args: Parsed arguments object
    """
    return __get_args(TsGlobals.TS_RUN_TO_COMPILE_ARGS, args)

