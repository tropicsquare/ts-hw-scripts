# -*- coding: utf-8 -*-

####################################################################################################
# Logging and Error codes support for Tropic Square digital scripting system
#
# TODO: License
####################################################################################################

import sys
import logging
import traceback
from enum import Enum, auto

from .ts_hw_global_vars import *


class TsColors:

    RED = '\033[91m'
    ORANGE = '\033[93m'
    GREEN = '\033[92m'
    PURPLE = '\033[95m'
    BLUE = '\033[96m'
    END = '\033[0m'
    NONE = None


class ColorMode:
    UseColors = False


class TSFormatter(logging.Formatter):

    COLORS = {
        logging.DEBUG: TsColors.BLUE,
        logging.INFO: TsColors.PURPLE,
        logging.WARNING: TsColors.ORANGE,
        logging.ERROR: TsColors.RED,
        logging.CRITICAL: TsColors.RED
    }

    def __init__(self, use_colors=True):
        if use_colors:
            log_format = "%(prefix)s%(levelname)s: %(message)s%(suffix)s"
            self.format = self._format_with_colors
        else:
            log_format = "%(levelname)s: %(message)s"
        super().__init__(fmt=log_format)

    def _format_with_colors(self, record):
        record.prefix = self.COLORS[record.levelno]
        record.suffix = TsColors.END
        return super().format(record)


####################################################################################################
# Error codes
####################################################################################################

class TsErrCode(Enum):
    """
    List of available error codes
    """

    # Generic error
    GENERIC = auto()

    # Config file errors
    ERR_CFG_8 = auto()
    ERR_CFG_13 = auto()
    ERR_CFG_22 = auto()
    ERR_CFG_23 = auto()

    # Source list file and test list file errors
    ERR_SLF_4 = auto()
    ERR_SLF_5 = auto()
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

    # Elaboration Errors
    ERR_ELB_0 = auto()
    ERR_ELB_2 = auto()
    ERR_ELB_3 = auto()

    # Simulation errors
    ERR_SIM_0 = auto()
    ERR_SIM_1 = auto()

    # Hook errors
    ERR_HOK_0 = auto()


# Pair between error code, and message to be printed.
__ERR_CODE_MSG_PAIR = {
    TsErrCode.GENERIC: lambda string: str(string),

    TsErrCode.ERR_CFG_8: lambda target, targets: "Invalid target '{}'. This target is not present "
                                                 "in simulation configuration file! Available "
                                                 "targets are: {}".format(target, targets),

    TsErrCode.ERR_CFG_13: lambda a, b: "'{}' and '{}' keywords in config file must be set "
                                       "together! It is not possible to set one without "
                                       "another!".format(a, b),

    TsErrCode.ERR_CFG_22: lambda: "When 'test_name_strategy=generic_parameter', 'test_name_generic' keyword must be defined "
                                  "(in VHDL top), or 'test_name_parameter' keyword must be defined (in Verilog /System Verilog top) "
                                  " and contain top level generic/parameter name.",

    TsErrCode.ERR_CFG_23: lambda error_message: f"Configuration is invalid > {error_message}",


    TsErrCode.ERR_SLF_4: lambda depth: "Depth {} exceeded when nesting source list files! "
                                      "Probably your list files contain circular reference".format(depth),

    TsErrCode.ERR_SLF_5: lambda file_name, lst_file: "Source file '{}' from list file '{} does not "
                                                "exist!".format(file_name, lst_file),

    TsErrCode.ERR_SLF_14: lambda pat: "No tests are matching '{}' names. Use '--list-tests' "
                                      "switch to get list of available tests!".format(pat),

    TsErrCode.ERR_SLF_15: lambda: "No test name was given. If you want to run a test you "
                                  "need to provide 'test_name' argument(s). Use '--list-tests' "
                                  "switch to show list of all available tests.",

    TsErrCode.ERR_SLF_17: lambda file_name, lf: "VHDL file '{}' in list file '{}' does not support "
                                           "define keyword! It is impossible to define macro in "
                                           "VHDL language!".format(file_name, lf),

    TsErrCode.ERR_SLF_18: lambda error_message, tlf: f"Test list file {tlf} is invalid > {error_message}",


    TsErrCode.ERR_CMP_0: lambda ext, file_name, sup: "Unknown file extension '.{}' of file '{}'. "
                                                "Supported file name extensions are: {}".format(
                                                ext, file_name, sup),

    TsErrCode.ERR_CMP_1: lambda lang, sim, langs: "Unsupported language '{}' by simulator '{}'. "
                                                  "Supported languages are: {}".format(lang, sim,
                                                                                       langs),

    TsErrCode.ERR_CMP_2: lambda exit_code: "Compilation failed with exit code {}. "
                                            "Check for correct syntax! ".format(exit_code),

    TsErrCode.ERR_CMP_3: lambda cmd, sim: "Compile command '{}' for simulator '{}' not available "
                                          "in PATH variable. Are you sure you have your "
                                          "environment properly configured?".format(cmd, sim),

    TsErrCode.ERR_CMP_4: lambda dir_name: "Compilation can not be launched from build directory itself "
                                     "({}). The reason is that '--clear' attribute can possibly "
                                     "erase the directory!".format(dir_name),

    TsErrCode.ERR_CMP_5: lambda signame: "Process aborted by external signal '{}'!".format(signame),

    TsErrCode.ERR_ELB_0: lambda top, code: "Elaboration failed on entity '{}' with exit code {}. "
                                           "".format(top, code),

    TsErrCode.ERR_ELB_2: lambda: "Elaboration and Simulation can not be run because no "
                                 "compiled files were found. Run 'ts_sim_compile.py' script "
                                 "first to compile source files for simulation!",

    TsErrCode.ERR_ELB_3: lambda file_name: "Elaboration can not be executed because simulator specific"
                                      "file '{}' created during compilation was not found! Are you "
                                      "sure you did not erase it by mistake?".format(file_name),

    TsErrCode.ERR_HOK_0: lambda file_name, hook: "Hook '{}' does not exist, or it failed when executing for hook: '{"
                                            "}'".format(file_name, hook),

    TsErrCode.ERR_SIM_0: lambda bin_file: "Simulation binary '{}' does not exist. Make sure that "
                                      "elaboration finished successfully!".format(bin_file),

    TsErrCode.ERR_SIM_1: lambda log_file: "Simulation log file '{}' does not exist.".format(log_file)
}


####################################################################################################
# Warning codes
####################################################################################################
class TsWarnCode(Enum):
    """
    List of available warning codes
    """
    GENERIC = auto()

    # Config file warnings
    WARN_CFG_1 = auto()


# Pair between error code, and message to be printed.
__WARN_CODE_MSG_PAIR = {
    # Generic warning
    TsWarnCode.GENERIC: lambda string: str(string),

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
    GENERIC = auto()

    # General info messages
    INFO_CMN_0 = auto()
    INFO_CMN_1 = auto()
    INFO_CMN_2 = auto()
    INFO_CMN_3 = auto()
    INFO_CMN_5 = auto()
    INFO_CMN_13 = auto()
    INFO_CMN_22 = auto()
    INFO_CMN_23 = auto()
    INFO_CMN_25 = auto()
    INFO_CMN_26 = auto()

    # Hook info messages
    INFO_HOK_0 = auto()
    INFO_HOK_1 = auto()


# Pair between error code, and message to be printed.
__INFO_CODE_MSG_PAIR = {
    # Generic info code
    TsInfoCode.GENERIC: lambda string: str(string),

    # Common config files
    TsInfoCode.INFO_CMN_0: lambda file_name: "Loading configuration file: '{}'".format(file_name),
    TsInfoCode.INFO_CMN_1: lambda: "Checking simulation configuration...",
    TsInfoCode.INFO_CMN_2: lambda: "Configuration OK!",
    TsInfoCode.INFO_CMN_3: lambda tgt: "Loading source list files for target: '{}'".format(tgt),
    TsInfoCode.INFO_CMN_5: lambda lib: "Compiling files for library: '{}'".format(lib),
    TsInfoCode.INFO_CMN_13: lambda tests: "Tests to be executed: {}".format(", ".join(tests)),
    TsInfoCode.INFO_CMN_22: lambda file_name: "Compiling file: {}".format(file_name),
    TsInfoCode.INFO_CMN_23: lambda: "Running recompilation before simulation! ",
    TsInfoCode.INFO_CMN_25: lambda tgt: "Loading source list files from dependent target: '{}'".format(tgt),
    TsInfoCode.INFO_CMN_26: lambda file_names: "Compiling files: {}".format(file_names),

    # Hook info messages
    TsInfoCode.INFO_HOK_0: lambda hook_name: "Calling hook: '{}'".format(hook_name),
    TsInfoCode.INFO_HOK_1: lambda hook_name: "Skipping unspecified hook: '{}'".format(hook_name),
}


def __ts_process_log(code, *opt_args):
    """
    Processes info/warning/error level code.
    :param code: info/warning/error code
    :param opt_args: Optional arguments passed to error code lambda function
    """
    choices = {
        TsInfoCode: (logging.info, __INFO_CODE_MSG_PAIR),
        TsWarnCode: (logging.warning, __WARN_CODE_MSG_PAIR),
        TsErrCode: (logging.error, __ERR_CODE_MSG_PAIR)
    }

    try:
        log_function, msg_pair = choices[type(code)]
    except KeyError:
        ts_script_bug("Logging code {} - type {} - is invalid, shall be one of the following types: {}".format(
            code, type(code), ", ".join(map(str, choices.keys()))))

    try:
        log_function(msg_pair[code](*opt_args))
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
    __ts_process_log(err_code, *opt_args)
    sys.exit(1)


def ts_warning(warn_code: TsWarnCode, *opt_args):
    """
    Throws colorized warning message for simple debug.
    :param warn_code: Warning code
    """
    __ts_process_log(warn_code, *opt_args)


def ts_info(info_code: TsInfoCode, *opt_args):
    """
    Throws colorized info message for simple debug.
    :param info_code: Info code
    """
    __ts_process_log(info_code, *opt_args)


def ts_debug(msg):
    """
    Prints debug line to a terminal.
    :param msg: Message to be shown. This is for developer only, so string is enough!
    """
    logging.debug(msg)


def ts_print(*args, color: TsColors = TsColors.NONE, big: bool = False, **kwargs):
    """
    Override builtin print function while adding some options
    """
    args = list(args)
    if big:
        args[0] = "*" * 80 + "\n" + str(args[0])
        args[-1] = str(args[-1]) + "\n" + "*" * 80
    if ColorMode.UseColors and color != TsColors.NONE:
        args[0] = color + str(args[0])
        args[-1] = str(args[-1]) + TsColors.END
    print(*args, **kwargs)


def ts_script_bug(msg):
    """
    Throw indication that this is bug in the scripting system and exception.
    :param msg: Message to be printed!
    """
    logging.error(msg)
    ts_print("Traceback",
            *traceback.format_stack(),
            "!! This a bug in scripting system. Report issue to developers !!",
            sep="\n", color=TsColors.RED)
    sys.exit(2)


def ts_configure_logging(args):
    """
    Configures logging based on command line arguments
    :args: Argparse command line arguments object.
    """
    if args.verbose >= 3:
        level = logging.DEBUG
    elif args.verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    ColorMode.UseColors = not args.no_color

    handler = logging.StreamHandler()
    handler.setFormatter(TSFormatter(ColorMode.UseColors))
    logging.basicConfig(level=level, handlers=[handler])

