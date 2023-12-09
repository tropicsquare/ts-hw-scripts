# -*- coding: utf-8 -*-

####################################################################################################
# Logging and Error codes support for Tropic Square digital scripting system
#
# For license see LICENSE file in repository root.
####################################################################################################

import logging
import sys
import traceback
from enum import Enum
from typing import Any, Optional, Protocol

from typing_extensions import NoReturn


class TsColors(str, Enum):

    RED = "\033[91m"
    ORANGE = "\033[93m"
    GREEN = "\033[92m"
    PURPLE = "\033[95m"
    BLUE = "\033[96m"
    END = "\033[0m"

    __str__ = str.__str__  # type: ignore


class ColorMode:
    UseColors = False


class TSFormatter(logging.Formatter):

    COLORS = {
        logging.DEBUG: TsColors.BLUE,
        logging.INFO: TsColors.PURPLE,
        logging.WARNING: TsColors.ORANGE,
        logging.ERROR: TsColors.RED,
        logging.CRITICAL: TsColors.RED,
    }

    def __init__(self, use_colors: bool = True):
        if use_colors:
            log_format = "%(prefix)s%(levelname)s: %(message)s%(suffix)s"
            self.format = self._format_with_colors
        else:
            log_format = "%(levelname)s: %(message)s"
        super().__init__(fmt=log_format)

    def _format_with_colors(self, record: logging.LogRecord):
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
    GENERIC = "%s"

    # Config file errors
    ERR_CFG_8 = (
        "Invalid target '%s'. This target is not present in simulation configuration file! "
        "Available targets are: %s"
    )
    ERR_CFG_23 = "Configuration is invalid > %s"

    # Source list file and test list file errors
    ERR_SLF_4 = (
        "Depth %s exceeded when nesting source list files! "
        "Probably your list files contain circular reference"
    )
    ERR_SLF_5 = "Source file '%s' from list file '%s' does not exist!"
    ERR_SLF_14 = (
        "No tests are matching '%s' names. "
        "Use '--list-tests' switch to get list of available tests!"
    )
    ERR_SLF_15 = (
        "No test name was given. "
        "If you want to run a test you need to provide 'test_name' argument(s). "
        "Use '--list-tests' switch to show list of all available tests."
    )
    ERR_SLF_17 = (
        "VHDL file '%s' in list file '%s' does not support 'define' keyword! "
        "It is impossible to define macro in VHDL language!"
    )
    ERR_SLF_18 = "List file %s is invalid > %s"
    ERR_SLF_19 = "Unable to find PDK object: %s, referred to by target %s"
    ERR_SLF_20 = (
        "Unable to find source list file: '%s', for pdk object '%s', "
        "available source list files for this pdk object: %s"
    )
    ERR_SLF_21 = (
        "Design config file is not loaded, you can't refer to PDK IPs/standard cells "
        "in simulation config file! Trying to refer to '%s' in target '%s'."
    )

    # Compilation errors
    ERR_CMP_0 = "Unknown file extension '.%s' of file '%s'. Supported file name extensions are: %s"
    ERR_CMP_1 = (
        "Language '%s' unsupported by simulator '%s'. Supported languages are: %s"
    )
    ERR_CMP_2 = "Compilation failed with exit code %s. Check for correct syntax!"
    ERR_CMP_3 = (
        "Compile command '%s' for simulator '%s' not available in PATH variable. "
        "Are you sure you have your environment properly configured?"
    )
    ERR_CMP_4 = (
        "Compilation can not be launched from build directory itself (%s). "
        "The reason is that '--clear' attribute can possibly erase the directory!"
    )
    ERR_CMP_5 = "Process aborted by external signal '%s'!"

    # Elaboration Errors
    ERR_ELB_0 = "Elaboration failed on entity '%s' with exit code %s. "
    ERR_ELB_2 = (
        "Elaboration and Simulation can not be run because no compiled files were found. "
        "Run 'ts_sim_compile.py' script first to compile source files for simulation!"
    )
    ERR_ELB_3 = (
        "Elaboration can not be executed because simulator specificfile '%s' "
        "created during compilation was not found! Are you sure you did not erase it by mistake?"
    )

    # Simulation errors
    ERR_SIM_0 = "Simulation binary '%s' does not exist. Make sure that elaboration finished successfully!"
    ERR_SIM_1 = "Simulation log file '%s' does not exist."

    # Hook errors
    ERR_HOK_0 = "Hook '%s' does not exist, or it failed when executing for hook: %s"

    # PDK config file errors
    ERR_PDK_0 = "PDK config file '%s' is invalid. \n %s"
    ERR_PDK_1 = "Failed to load design config file '%s'. \n %s"
    ERR_PDK_2 = "Design config file is invalid. \n %s"
    ERR_PDK_3 = "PDK configuration file: '%s' does not exist."
    ERR_PDK_4 = "Invalid corner '%s' for '%s'. Defined corners are: '%s'."
    ERR_PDK_5 = "View '%s' does not exist for '%s'"
    ERR_PDK_6 = "PDK '%s' set in design config file not available. Loaded PDKs: '%s'"
    ERR_PDK_7 = "Standard cells '%s(%s)' not available in PDK '%s'. Available standard cells: '%s'"
    ERR_PDK_8 = "IP '%s(%s)' not found in target PDK '%s'. Available IPs: '%s'"
    ERR_PDK_9 = "IP '%s' not found in target PDK '%s'. No IPs available in this PDK!"
    ERR_PDK_10 = (
        "Invalid corner '%s' for mode '%s'. Available corners in '%s' PDK: '%s'"
    )
    ERR_PDK_11 = "Constraint file '%s' for mode '%s' not found"
    ERR_PDK_12 = "%s '%s(%s)' defined multiple times"
    ERR_PDK_13 = "Unknown view '%s' to export. Known views are : '%s'"
    ERR_PDK_14 = (
        "Only one standard cell can be defined as target standard cell in the design. "
        "Currently, following are defined: %s"
    )
    ERR_PDK_15 = (
        "Target '%s' defined as PD design top does not exist in simulation config file. "
        "Existing targets are: %s"
    )
    ERR_PDK_16 = "Global constraint file: '%s' does not exist"
    ERR_PDK_17 = "Floorplan file: '%s' does not exist"
    ERR_PDK_18 = "SPEF file '%s' for mode '%s' not found"
    ERR_PDK_19 = "Specified flow directory %s: %s not found"
    ERR_PDK_20 = "Specified map file %s does not exist"
    ERR_PDK_21 = "Tlu+ file '%s' for mode '%s' not found"
    ERR_PDK_22 = "Specified tech file %s does not exist"
    ERR_PDK_23 = (
        "Specified %s operation condition does not match with the %s file content"
    )
    ERR_PDK_24 = "Design config file '%s' not found, can't continue!"
    ERR_PDK_25 = "'%s(%s)' is missing view '%s', but the view is required"
    ERR_PDK_26 = (
        "When running ts_syn_run.py with '--topo', "
        "global 'constraints' keyword must be defined in Design config file under 'design'."
    )

    # Power error messages
    ERR_PWR_0 = "Power config file is invalid.\n %s"
    ERR_PWR_1 = "Power config file not found."
    ERR_PWR_2 = "Failed to load power config file '%s'. \n %s"

    ERR_SYN_0 = "Missing runcode parameter"
    ERR_SYN_1 = "Cannot open %s runcode directory. It doesn't exist"
    ERR_SYN_2 = "Directory runcode %s already exists. Use --force swith if you want to re-write it"
    ERR_STA_0 = "Missing runcode parameter"
    ERR_STA_1 = "Cannot open %s runcode directory. It doesn't exist"
    ERR_STA_2 = "Directory runcode %s already exists. Use --force swith if you want to re-write it"
    ERR_STA_3 = "Source --source %s is not matching flow_dirs"
    ERR_STA_4 = "Netlist %s was not found"
    ERR_STA_5 = "Mode %s was not found"
    ERR_STA_6 = "Either --dmsa or --mode <mode_name> must be used."
    ERR_STA_7 = "Switch --open-result shall not be used with --dmsa switch."

    # DFT error messages
    ERR_DFT_0 = "Missing runcode parameter"
    ERR_DFT_1 = "Cannot open %s runcode directory. It doesn't exist."
    ERR_DFT_2 = "Directory runcode %s already exists. Use --force swith if you want to re-write it"
    ERR_DFT_3 = "DFT root_dir cannot be selected properly."
    ERR_DFT_4 = "Netlist %s was not found"
    ERR_DFT_5 = "Missing dft constraint file"

    # PNR error messages
    ERR_PNR_0 = "Missing runcode parameter"
    ERR_PNR_1 = "Cannot open %s runcode directory. It doesn't exist."
    ERR_PNR_2 = "Directory runcode %s already exists. Use --force swith if you want to re-write it"
    ERR_PNR_3 = "Source --source %s is not matching flow_dirs"
    ERR_PNR_4 = "Netlist %s was not found"


####################################################################################################
# Warning codes
####################################################################################################
class TsWarnCode(Enum):
    """
    List of available warning codes
    """

    # Generic warning
    GENERIC = "%s"

    # Config file warnings
    WARN_CFG_1 = "Key '%s' not defined in simulation configuration file. Assuming '%s' by default."

    # PDK / Design config file warnings
    WARN_PDK_1 = "Design config file not found -> Skipping initialization."
    WARN_PDK_2 = "'%s' corner for '%s' not defined!"
    WARN_PDK_3 = "'%s(%s)' is missing view '%s', not exporting."
    WARN_PDK_4 = "'%s(%s)' is missing view '%s' for corner: '%s', not exporting."
    WARN_PDK_5 = "Floorplan not defined, but export attempted!"
    WARN_PDK_6 = (
        "No views added, skipping TCL export. "
        "Use '--add-views=<views>' to define which views you would like to export."
    )
    WARN_PDK_7 = "Map file is not defined, but export attempted!"
    WARN_PDK_8 = "Spef file is not defined, but export attempted!"
    WARN_PDK_9 = "Tlu+ file is not defined, but export attempted!"
    WARN_PDK_10 = "RC corner is not defined, but export attempted!"
    WARN_PDK_11 = "Flow dirs are not defined, but export attempted!"


####################################################################################################
# Information codes
####################################################################################################
class TsInfoCode(Enum):
    """
    List of available informational codes
    """

    # Generic info
    GENERIC = "%s"

    # General info messages
    INFO_CMN_0 = "Loading simulation configuration file: '%s'"
    INFO_CMN_1 = "Checking simulation configuration..."
    INFO_CMN_2 = "Simulation Configuration OK!"
    INFO_CMN_3 = "Loading source list files for target: '%s'"
    INFO_CMN_5 = "Compiling files for library: '%s'"
    INFO_CMN_13 = "Tests to be executed: %s"
    INFO_CMN_22 = "Compiling file: %s"
    INFO_CMN_23 = "Running recompilation before simulation! "
    INFO_CMN_25 = "Loading source list files from dependent target: '%s'"
    INFO_CMN_26 = "Compiling files: %s"

    # Hook info messages
    INFO_HOK_0 = "Calling hook: '%s'"
    INFO_HOK_1 = "Skipping unspecified hook: '%s'"

    # PDK config info messages
    INFO_PDK_0 = "Loading PDK configuration file: '%s'"
    INFO_PDK_1 = "Loading Design configuration file: '%s'"
    INFO_PDK_2 = "Checking design configuration..."
    INFO_PDK_3 = "Design configuration OK!"
    INFO_PDK_4 = "Loading PDK: %s"
    INFO_PDK_5 = "Exporting design configuration to: '%s'"

    # PWR info messages
    INFO_PWR_0 = "Loading Power configuration file: '%s'"

    # Syn flow info messages
    INFO_SYS_0 = "Selected runcode is: %s"
    INFO_SYS_1 = "Opening synthesis database: %s"
    INFO_SYS_2 = "Deleting and creating new synthesis database: %s"
    INFO_SYS_3 = "Following %s cmd to be executed: %s"
    INFO_SYS_4 = "Creating folder: %s"
    INFO_SYS_5 = "Deleting folder: %s"

    # STA flow info messages
    INFO_STA_0 = "Selected runcode is: %s"
    INFO_STA_1 = "Opening sta database: %s"
    INFO_STA_2 = "Deleting and creating new sta database: %s"
    INFO_STA_3 = "Following %s cmd to be executed: %s"
    INFO_STA_4 = "Creating folder: %s"
    INFO_STA_5 = "Deleting folder: %s"

    # DFT flow messages
    INFO_DFT_0 = "Selected runcode is: %s"
    INFO_DFT_1 = "Opening DFT database: %s"
    INFO_DFT_2 = "Deleting and creating new DFT database: %s"
    INFO_DFT_3 = "Following %s cmd to be executed: %s"
    INFO_DFT_4 = "Creating folder: %s"
    INFO_DFT_5 = "Deleting folder: %s"

    # PNR flow info messages
    INFO_PNR_0 = "Selected runcode is: %s"
    INFO_PNR_1 = "Opening PnR database: %s"
    INFO_PNR_2 = "Deleting and creating new PnR database: %s"
    INFO_PNR_3 = "Following %s cmd to be executed: %s"
    INFO_PNR_4 = "Creating folder: %s"
    INFO_PNR_5 = "Deleting folder: %s"


####################################################################################################
# Codes formatting
####################################################################################################


def __ts_process_log(code: Enum, *opt_args: Any) -> str:
    assert isinstance(code.value, str)
    try:
        return code.value % opt_args
    except TypeError:
        ts_script_bug(f"Invalid number of arguments to info/warning/error code: {code}")


####################################################################################################
####################################################################################################
# Public API
####################################################################################################
####################################################################################################


def ts_throw_error(err_code: TsErrCode, *opt_args: Any) -> NoReturn:
    """
    Throws colorized error message for simple debug.
    :param err_code: Error code
    """
    logging.error(__ts_process_log(err_code, *opt_args))
    sys.exit(1)


def ts_warning(warn_code: TsWarnCode, *opt_args: Any) -> None:
    """
    Throws colorized warning message for simple debug.
    :param warn_code: Warning code
    """
    logging.warning(__ts_process_log(warn_code, *opt_args))


def ts_info(info_code: TsInfoCode, *opt_args: Any) -> None:
    """
    Throws colorized info message for simple debug.
    :param info_code: Info code
    """
    logging.info(__ts_process_log(info_code, *opt_args))


def ts_debug(msg: object) -> None:
    """
    Prints debug line to a terminal.
    :param msg: Message to be shown. This is for developer only, so string is enough!
    """
    logging.debug(msg)


def ts_print(
    *args: str, color: Optional[TsColors] = None, big: bool = False, **kwargs: Any
) -> None:
    """
    Override builtin print function while adding some options
    """
    _args = list(args)
    if big:
        _args[0] = "*" * 80 + "\n" + str(_args[0])
        _args[-1] = str(_args[-1]) + "\n" + "*" * 80
    if ColorMode.UseColors and color is not None:
        _args[0] = color + str(_args[0])
        _args[-1] = str(_args[-1]) + TsColors.END
    print(*_args, **kwargs)


def ts_script_bug(msg: object) -> NoReturn:
    """
    Throw indication that this is bug in the scripting system and exception.
    :param msg: Message to be printed!
    """
    logging.error(msg)
    ts_print(
        "Traceback",
        *traceback.format_stack(),
        "!! This a bug in scripting system. Report issue to developers !!",
        sep="\n",
        color=TsColors.RED,
    )
    sys.exit(2)


class LoggingConfiguration(Protocol):
    verbose: int
    no_color: bool


def ts_configure_logging(args: LoggingConfiguration) -> None:
    """
    Configures logging based on command line arguments
    :args: Argparse command line arguments object.
    """
    try:
        level = [
            logging.ERROR,  # 0
            logging.WARNING,  # 1
            logging.INFO,  # 2
        ][args.verbose]
    except IndexError:
        level = logging.DEBUG  # >= 3

    ColorMode.UseColors = not args.no_color

    handler = logging.StreamHandler()
    handler.setFormatter(TSFormatter(ColorMode.UseColors))
    logging.basicConfig(level=level, handlers=[handler])
