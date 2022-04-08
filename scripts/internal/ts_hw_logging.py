# -*- coding: utf-8 -*-

####################################################################################################
# Logging and Error codes support for Tropic Square digital scripting system
#
# TODO: License
####################################################################################################

import logging
import traceback
from enum import Enum, auto
import sys

from .ts_hw_global_vars import *

# ANSI codes for colors
# KISS - Avoid using fancy packages with coloring
CRED = '\033[91m'
CORANGE = '\033[93m'
CGREEN = '\033[92m'
CPURPLE = '\033[95m'
CBLUE = '\033[96m'
CEND = '\033[0m'


class NoColorMode:
    NoColor = False

####################################################################################################
# Error codes
####################################################################################################

class TsErrCode(Enum):
    """
    List of available error codes
    """

    # Generic error
    ERR_GENERIC = auto()

    # Config file errors
    ERR_CFG_0 = auto()
    ERR_CFG_1 = auto()
    ERR_CFG_8 = auto()
    ERR_CFG_13 = auto()
    ERR_CFG_22 = auto()
    ERR_CFG_23 = auto()

    # Source list file and test list file errors
    ERR_SLF_0 = auto()
    ERR_SLF_1 = auto()
    ERR_SLF_4 = auto()
    ERR_SLF_5 = auto()
    ERR_SLF_7 = auto()
    ERR_SLF_12 = auto()
    ERR_SLF_14 = auto()
    ERR_SLF_15 = auto()
    ERR_SLF_17 = auto()
    ERR_SLF_18 = auto()

    # Compilation errors
    ERR_CMP_0 = auto()
    ERR_CMP_1 = auto()
    ERR_CMP_2 = auto()
    ERR_CMP_3 = auto()
    ERR_CMP_4 = auto()
    ERR_CMP_5 = auto()
    ERR_CMP_6 = auto()

    # Elaboration Errors
    ERR_ELB_0 = auto()
    ERR_ELB_2 = auto()
    ERR_ELB_3 = auto()

    # Environment errors
    ERR_ENV_0 = auto()

    # Simulation errors
    ERR_SIM_0 = auto()
    ERR_SIM_1 = auto()

    # Hook errors
    ERR_HOK_0 = auto()


# Pair between error code, and message to be printed.
__ERR_CODE_MSG_PAIR = {
    TsErrCode.ERR_GENERIC: lambda string: "{}".format(string),

    TsErrCode.ERR_CFG_0: lambda: "${}/{} config file was not found. Make sure it exists!".format(
                                   TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_CFG_PATH),

    TsErrCode.ERR_CFG_1: lambda: "Failed to load ${}/{} config file probably due to incorrect YAML "
                                 "syntax. Check its syntax".format(TsGlobals.TS_REPO_ROOT,
                                                                   TsGlobals.TS_SIM_CFG_PATH),

    TsErrCode.ERR_CFG_8: lambda target, targets: "Invalid target '{}'. This target is not present "
                                                 "in simulation configuration file! Available "
                                                 "targets are: {}".format(target, targets),

    TsErrCode.ERR_CFG_13: lambda a, b: "'{}' and '{}' keywords in config file must be set "
                                       "together! It is not possible to set one without "
                                       "another!".format(a, b),

    TsErrCode.ERR_CFG_22: lambda: "When 'test_name_strategy=generic_parameter', 'test_name_generic' keyword must be defined "
                                  "(in VHDL top), or 'test_name_parameter' keyword must be defined (in Verilog /System Verilog top) "
                                  " and contain top level generic/parametr name.",

    TsErrCode.ERR_CFG_23: lambda error_message: f"Configuration is invalid > {error_message}",


    TsErrCode.ERR_SLF_0: lambda source_list_file: "Source list file: '{}' does not exist!".
                                                  format(source_list_file),

    TsErrCode.ERR_SLF_1: lambda lf: "Failed to load '{}' list file probably due to "
                                    "incorrect YAML syntax. Check syntax of the file".format(lf),

    TsErrCode.ERR_SLF_4: lambda path: "Depth {} exceeded when nesting source list files! "
                                      "Probably your list files contain circular reference".format(
                                      path),

    TsErrCode.ERR_SLF_5: lambda file, src_file: "Source file '{}' from list file '{} does not "
                                                "exist!".format(file, src_file),

    TsErrCode.ERR_SLF_7: lambda file: "List file '{}' shall end with '.yml' suffix (YAML file "
                                      "extension). ".format(file),

    TsErrCode.ERR_SLF_12: lambda chars, val, path: "Invalid character(s) '{}' in attribute value '{"
                                                  "}' in file '{}'".format(", ".join(chars), val, path),

    TsErrCode.ERR_SLF_14: lambda pat: "No tests are matching '{}' names. Use '--list-tests' "
                                      "switch to get list of available tests!".format(pat),

    TsErrCode.ERR_SLF_15: lambda: "No test name was given. If you want to run a test you "
                                  "need to provide 'test_name' argument(s). Use '--list-tests' "
                                  "switch to show list of all available tests.",

    TsErrCode.ERR_SLF_17: lambda file, lf: "VHDL file '{}' in list file '{}' does not support "
                                           "define keyword! It is impossible to define macro in "
                                           "VHDL language!".format(file, lf),

    TsErrCode.ERR_SLF_18: lambda error_message, tlf: f"Test list file {tlf} is invalid > {error_message}",


    TsErrCode.ERR_CMP_0: lambda ext, file, sup: "Unknown file extension '.{}' of file '{}'. "
                                                "Supported file name extensions are: {}".format(
                                                ext, file, sup),

    TsErrCode.ERR_CMP_1: lambda lang, sim, langs: "Unsupported language '{}' by simulator '{}'. "
                                                  "Supported languages are: {}".format(lang, sim,
                                                                                       langs),

    TsErrCode.ERR_CMP_2: lambda file, code: "Compilation failed on file '{}' with exit code {}. "
                                            "Check if has correct syntax! ".format(file, code),

    TsErrCode.ERR_CMP_3: lambda cmd, sim: "Compile command '{}' for simulator '{}' not available "
                                          "in PATH variable. Are you sure you have your "
                                          "environment properly configured?".format(cmd, sim),

    TsErrCode.ERR_CMP_4: lambda dir: "Compilation can not be launched from build directory itself "
                                     "({}). The reason is that '--clear' attribute can possibly "
                                     "erase the directory!".format(dir),

    TsErrCode.ERR_CMP_5: lambda signame: "Process aborted by external signal '{}'!".format(signame),

    TsErrCode.ERR_CMP_6: lambda orig_tgt, dep_tgt: "Target '{}' depends on target '{}' which does "
                                        "not exist. Run 'ts_sim_compile.py <dummy>' to see all "
                                        "available targets".format(orig_tgt, dep_tgt),

    TsErrCode.ERR_ELB_0: lambda top, code: "Elaboration failed on entity '{}' with exit code {}. "
                                           "".format(top, code),

    TsErrCode.ERR_ELB_2: lambda: "Elaboration and Simulation can not be run because no "
                                 "compiled files were found. Run 'ts_sim_compile.py' script "
                                 "first to compile source files for simulation!",

    TsErrCode.ERR_ELB_3: lambda file: "Elaboration can not be executed because simulator specific"
                                      "file '{}' created during compilation was not found! Are you "
                                      "sure you did not erase it by mistake?",


    TsErrCode.ERR_ENV_0: lambda: "{} Environment variable is not defined! Run '{}' script.".format(
                                  TsGlobals.TS_REPO_ROOT, TsGlobals.TS_CONFIG_ENV_SCRIPT),


    TsErrCode.ERR_HOK_0: lambda file, hook: "Hook '{}' does not exist, or it failed when executing for hook: '{"
                                            "}'".format(file, hook),

    TsErrCode.ERR_SIM_0: lambda file: "Simulation binary '{}' does not exist. Make sure that "
                                      "elaboration finished successfully!".format(file),

    TsErrCode.ERR_SIM_1: lambda file: "Simulation log file '{}' does not exist.".format(file)
}


####################################################################################################
# Warning codes
####################################################################################################
class TsWarnCode(Enum):
    """
    List of available warning codes
    """
    WARN_GENERIC = auto()

    # Config file warnings
    WARN_CFG_1 = auto()


# Pair between error code, and message to be printed.
__WARN_CODE_MSG_PAIR = {
    # Generic warning
    TsWarnCode.WARN_GENERIC: lambda string: "{}".format(string),

    # Configuration file warnings
    TsWarnCode.WARN_CFG_1: lambda key, def_val: "Key '{}' not defined in simulation configuration file. "
                                                "Assuming '{}' by default.".format(key, def_val),
}


####################################################################################################
# Information codes
####################################################################################################
class TsInfoCode(Enum):
    """
    List of available informational codes
    """
    INFO_GENERIC = auto()

    # General info messages
    INFO_CMN_0 = auto()
    INFO_CMN_1 = auto()
    INFO_CMN_2 = auto()
    INFO_CMN_3 = auto()
    INFO_CMN_4 = auto()
    INFO_CMN_5 = auto()
    INFO_CMN_6 = auto()
    INFO_CMN_7 = auto()
    INFO_CMN_8 = auto()
    INFO_CMN_9 = auto()
    INFO_CMN_10 = auto()
    INFO_CMN_11 = auto()
    INFO_CMN_13 = auto()
    INFO_CMN_14 = auto()
    INFO_CMN_15 = auto()
    INFO_CMN_21 = auto()
    INFO_CMN_22 = auto()
    INFO_CMN_23 = auto()
    INFO_CMN_24 = auto()
    INFO_CMN_25 = auto()

    # Hook info messages
    INFO_HOK_0 = auto()
    INFO_HOK_1 = auto()


# Pair between error code, and message to be printed.
__INFO_CODE_MSG_PAIR = {
    # Generic info code
    TsInfoCode.INFO_GENERIC: lambda string: "{}".format(string),

    # Common config files
    TsInfoCode.INFO_CMN_0: lambda file: "Loading configuration file: '{}'".format(file),
    TsInfoCode.INFO_CMN_1: lambda: "Checking simulation configuration...",
    TsInfoCode.INFO_CMN_2: lambda: "Configuration OK!",
    TsInfoCode.INFO_CMN_3: lambda tgt: "Loading source list files for target: '{}'".format(tgt),
    TsInfoCode.INFO_CMN_4: lambda: "Source files available:",
    TsInfoCode.INFO_CMN_5: lambda lib: "Compiling files for library: '{}'".format(lib),
    TsInfoCode.INFO_CMN_6: lambda: " Compilation starting ",
    TsInfoCode.INFO_CMN_7: lambda: "!! Compilation successful !! ",
    TsInfoCode.INFO_CMN_8: lambda: "Running elaboration:",
    TsInfoCode.INFO_CMN_9: lambda: "!! Elaboration successful !!",
    TsInfoCode.INFO_CMN_10: lambda: "Launching simulation:",
    TsInfoCode.INFO_CMN_11: lambda: "!! Simulation done !!",
    TsInfoCode.INFO_CMN_13: lambda: "Tests to be executed:",
    TsInfoCode.INFO_CMN_14: lambda test_name: "Starting test: {}".format(test_name),
    TsInfoCode.INFO_CMN_15: lambda file: "Loading test list file: {}".format(file),
    TsInfoCode.INFO_CMN_21: lambda: "List available targets:",
    TsInfoCode.INFO_CMN_22: lambda file: "Compiling file: {}".format(file),
    TsInfoCode.INFO_CMN_23: lambda: "Running recompilation before simulation! ",
    TsInfoCode.INFO_CMN_24: lambda tool, file: "Exporting {} TCL file: {}".format(tool, file),
    TsInfoCode.INFO_CMN_25: lambda tgt: "Loading source list files from dependant target: '{}'".format(tgt),

    # Hook info messages
    TsInfoCode.INFO_HOK_0: lambda hook_name: "Calling hook: '{}'".format(hook_name),
    TsInfoCode.INFO_HOK_1: lambda hook_name: "No hook file specified for hook: '{}' -> "
                                             "Skipping hook".format(hook_name),
}


def ts_process_log(code, *opt_args):
    """
    Processes info/warning/error level code.
    :param code: info/warning/error code
    :param opt_args: Optional arguments passed to error code lambda!
    """
    func = None
    if isinstance(code, TsErrCode):
        color = CRED
        color_end = CEND
        func = logging.error
        pair = __ERR_CODE_MSG_PAIR
        title = "ERROR"
    elif isinstance(code, TsWarnCode):
        color = CORANGE
        color_end = CEND
        func = logging.warning
        pair = __WARN_CODE_MSG_PAIR
        title = "WARNING"
    elif isinstance(code, TsInfoCode):
        color = CPURPLE
        color_end = CEND
        func = logging.info
        pair = __INFO_CODE_MSG_PAIR
        title = "INFO"

    else:
        ts_script_bug("Invalid type of logging code. Shall be info/warning/error code!")

    if NoColorMode.NoColor:
        color = ""
        color_end = ""

    try:
        func(f"{color}{title}: {pair[code](*opt_args)}{color_end}")
    except TypeError:
        ts_script_bug(f"Invalid number of arguments to info/warning/error code: {code}")


####################################################################################################
####################################################################################################
# Public API
####################################################################################################
####################################################################################################


def ts_throw_error(err_code: TsErrCode, *opt_args):
    """
    Throws colorized error message for simple debug.
    :param err_code: Error code
    """
    ts_process_log(err_code, *opt_args)
    sys.exit(1)


def ts_warning(warn_code: TsWarnCode, *opt_args):
    """
    Throws colorized warning message for simple debug.
    :param warn_code: Warning code
    """
    ts_process_log(warn_code, *opt_args)

def ts_debug(msg):
    """
    Prints debug line to a terminal.
    :param msg: Message to be shown. This is for developer only, so string is enough!
    """
    logging.debug(CBLUE + "DEBUG: " + str(msg) + CEND)


def ts_info(info_code: TsInfoCode, *opt_args):
    """
    Throws colorized info message for simple debug.
    :param info_code: Info code
    """
    ts_process_log(info_code, *opt_args)


def ts_big_info(info_code: TsInfoCode, *opt_args):
    """
    Throws big colorized info message for simple debug.
    :param info_code: Info code
    """
    ts_process_log(TsInfoCode.INFO_GENERIC, "*" * 80)
    ts_process_log(info_code, *opt_args)
    ts_process_log(TsInfoCode.INFO_GENERIC, "*" * 80)


def ts_script_bug(msg):
    """
    Throw indication that this is bug in the scripting system and exception.
    :param msg: Message to be printed!
    """
    logging.error(CRED + "Trace-back:" + CEND)
    for line in traceback.format_stack():
        print(line)
    logging.error(CRED + "!! This a bug  in scripting system. Report it to its developers !!" +
                  CEND)
    logging.error(CRED + "BUG: " + msg + CEND)
    sys.exit(2)


def ts_configure_logging(args):
    """
    Configures logging based on command line arguments
    :args: Argparse command line arguments object.
    """
    if args.verbose == 3:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    elif args.verbose >= 1:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(message)s')

    if args.no_color:
        NoColorMode.NoColor = True
