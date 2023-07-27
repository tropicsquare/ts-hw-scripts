# -*- coding: utf-8 -*-

####################################################################################################
# Logging and Error codes support for Tropic Square digital scripting system
#
# TODO: License
####################################################################################################

import logging
import sys
import traceback
from enum import Enum


class TsColors:

    RED = "\033[91m"
    ORANGE = "\033[93m"
    GREEN = "\033[92m"
    PURPLE = "\033[95m"
    BLUE = "\033[96m"
    END = "\033[0m"
    NONE = None


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
# Generic Log enumeration
####################################################################################################


class LogEnum(Enum):
    def __call__(self, *args):
        return self.value[0](*args)


####################################################################################################
# Error codes
####################################################################################################


class TsErrCode(LogEnum):
    """
    List of available error codes
    """

    # Generic error
    GENERIC = [lambda string: str(string)]

    # Config file errors
    ERR_CFG_8 = [
        lambda target, targets: "Invalid target '{}'. This target is not present "
        "in simulation configuration file! Available "
        "targets are: {}".format(target, targets)
    ]
    ERR_CFG_23 = [lambda error_message: f"Configuration is invalid > {error_message}"]

    # Source list file and test list file errors
    ERR_SLF_4 = [
        lambda depth: "Depth {} exceeded when nesting source list files! "
        "Probably your list files contain circular reference".format(depth)
    ]
    ERR_SLF_5 = [
        lambda file_name, lst_file: "Source file '{}' from list file '{} does not "
        "exist!".format(file_name, lst_file)
    ]
    ERR_SLF_14 = [
        lambda pat: "No tests are matching '{}' names. Use '--list-tests' "
        "switch to get list of available tests!".format(pat)
    ]
    ERR_SLF_15 = [
        lambda: "No test name was given. If you want to run a test you "
        "need to provide 'test_name' argument(s). Use '--list-tests' "
        "switch to show list of all available tests."
    ]
    ERR_SLF_17 = [
        lambda file_name, lf: "VHDL file '{}' in list file '{}' does not support "
        "define keyword! It is impossible to define macro in "
        "VHDL language!".format(file_name, lf)
    ]
    ERR_SLF_18 = [
        lambda error_message, tlf: f"List file {tlf} is invalid > {error_message}"
    ]
    ERR_SLF_19 = [
        lambda pdk_obj, tgt: f"Unable to find PDK object: {pdk_obj}, reffered to by target {tgt}"
    ]
    ERR_SLF_20 = [
        lambda slf, pdk_obj, allowed: f"Unable to find source list file: '{slf}', for pdk object '{pdk_obj}', available source list files for this pdk object: {allowed}"
    ]
    ERR_SLF_21 = [
        lambda obj, target: f"Design config file is not loaded, you can't reffer to PDK IPs/standard cells in simulation config file! Trying to reffer to '{obj}' in target '{target}'."
    ]

    # Compilation errors
    ERR_CMP_0 = [
        lambda ext, file_name, sup: "Unknown file extension '.{}' of file '{}'. "
        "Supported file name extensions are: {}".format(ext, file_name, sup)
    ]
    ERR_CMP_1 = [
        lambda lang, sim, langs: "Unsupported language '{}' by simulator '{}'. "
        "Supported languages are: {}".format(lang, sim, langs)
    ]
    ERR_CMP_2 = [
        lambda exit_code: "Compilation failed with exit code {}. "
        "Check for correct syntax! ".format(exit_code)
    ]
    ERR_CMP_3 = [
        lambda cmd, sim: "Compile command '{}' for simulator '{}' not available "
        "in PATH variable. Are you sure you have your "
        "environment properly configured?".format(cmd, sim)
    ]
    ERR_CMP_4 = [
        lambda dir_name: "Compilation can not be launched from build directory itself "
        "({}). The reason is that '--clear' attribute can possibly "
        "erase the directory!".format(dir_name)
    ]
    ERR_CMP_5 = [
        lambda signame: "Process aborted by external signal '{}'!".format(signame)
    ]

    # Elaboration Errors
    ERR_ELB_0 = [
        lambda top, code: "Elaboration failed on entity '{}' with exit code {}. "
        "".format(top, code)
    ]
    ERR_ELB_2 = [
        lambda: "Elaboration and Simulation can not be run because no "
        "compiled files were found. Run 'ts_sim_compile.py' script "
        "first to compile source files for simulation!"
    ]
    ERR_ELB_3 = [
        lambda file_name: "Elaboration can not be executed because simulator specific"
        "file '{}' created during compilation was not found! Are you "
        "sure you did not erase it by mistake?".format(file_name)
    ]

    # Simulation errors
    ERR_SIM_0 = [
        lambda bin_file: "Simulation binary '{}' does not exist. Make sure that "
        "elaboration finished successfully!".format(bin_file)
    ]
    ERR_SIM_1 = [
        lambda log_file: "Simulation log file '{}' does not exist.".format(log_file)
    ]

    # Hook errors
    ERR_HOK_0 = [
        lambda file_name, hook: "Hook '{}' does not exist, or it failed when executing for hook: '{"
        "}'".format(file_name, hook)
    ]

    # PDK config file errors
    ERR_PDK_0 = [
        lambda e, pdk_file: "PDK config file '{}' is invalid. \n {}".format(pdk_file, e)
    ]
    ERR_PDK_1 = [
        lambda e, design_file: "Failed to load design config file '{}'. \n {}".format(
            design_file, e
        )
    ]
    ERR_PDK_2 = [lambda e: "Design config file is invalid. \n {}".format(e)]
    ERR_PDK_3 = [
        lambda path: "PDK configuration file: '{}' does not exist \n".format(path)
    ]
    ERR_PDK_4 = [
        lambda corner, instance, allowed: "Invalid corner '{}' for '{}'. Defined corners are: '{}'. \n".format(
            corner, instance, allowed
        )
    ]
    ERR_PDK_5 = [
        lambda instance, path: "View '{}' does not exist for '{}'".format(
            path, instance
        )
    ]
    ERR_PDK_6 = [
        lambda pdk_name, allowed: "PDK '{}' set in design config file not available. Loaded PDKs: '{}'".format(
            pdk_name, allowed
        )
    ]
    ERR_PDK_7 = [
        lambda pdk_name, std_cells, version, allowed: "Standard cells '{}({})' not available in PDK '{}'. Available standard cells: '{}'".format(
            std_cells, version, pdk_name, allowed
        )
    ]
    ERR_PDK_8 = [
        lambda ip_name, ip_version, pdk_name, allowed: "IP '{}({})' not found in target PDK '{}'. Available IPs: '{}'".format(
            ip_name, ip_version, pdk_name, allowed
        )
    ]
    ERR_PDK_9 = [
        lambda ip_name, pdk_name: "IP '{}' not found in target PDK '{}'. No IPs available in this PDK!".format(
            ip_name, pdk_name
        )
    ]
    ERR_PDK_10 = [
        lambda mode, corner, pdk, allowed: "Invalid corner '{}' for mode '{}'. Available corners in '{}' PDK: '{}'".format(
            corner, mode, pdk, allowed
        )
    ]
    ERR_PDK_11 = [
        lambda constraint, mode: "Constraint file '{}' for mode '{}' not found".format(
            constraint, mode
        )
    ]
    ERR_PDK_12 = [
        lambda obj_type, obj_name, version: "{} '{}({})' defined multiple times".format(
            obj_type, obj_name, version
        )
    ]
    ERR_PDK_13 = [
        lambda view, allowed: "Unknown view '{}' to export. Known views are : '{}'".format(
            view, allowed
        )
    ]
    ERR_PDK_14 = [
        lambda vals: "Only one standard cells can be defined as target standard cells in the design. Currently, following are defined: {}".format(
            vals
        )
    ]
    ERR_PDK_15 = [
        lambda target, allowed: "Target '{}' defined as PD design top does not exist in simulation config file. Existing targets are: {}".format(
            target, allowed
        )
    ]
    ERR_PDK_16 = [
        lambda file: "Global constraint file: '{}' does not exist".format(file)
    ]
    ERR_PDK_17 = [lambda file: "Floorplan file: '{}' does not exist".format(file)]
    ERR_PDK_18 = [
        lambda spef, mode: "SPEF file '{}' for mode '{}' not found".format(spef, mode)
    ]
    ERR_PDK_19 = [
        lambda dir, path: "Specified flow directory {}: {} not found".format(dir, path)
    ]
    ERR_PDK_20 = [lambda file: "Specified map file {} does not exist".format(file)]
    ERR_PDK_21 = [
        lambda tluplus, mode: "Tlu+ file '{}' for mode '{}' not found".format(
            tluplus, mode
        )
    ]
    ERR_PDK_22 = [lambda file: "Specified tech file {} does not exist".format(file)]
    ERR_PDK_23 = [
        lambda opcond, file: "Specified {} operation condition does not match with the {} file contant".format(
            opcond, file
        )
    ]
    ERR_PDK_24 = [
        lambda file: "Design config file '{}' not found, can't continue!".format(file)
    ]

    ERR_PDK_25 = [
        lambda name, version, view: "'{}({})' is missing view '{}', but the view is required".format(
            name, version, view
        )
    ]

    ERR_PDK_26 = [
        lambda: "When running ts_syn_run.py with \"--topo\", global \"constraints\" keyword must be "
                "defined in Design config file under \"design\"."
    ]

    # Power error messages
    ERR_PWR_0 = [lambda e: "Power config file is invalid.\n {}".format(e)]
    ERR_PWR_1 = [lambda: "Power config file not found. \n {}"]
    ERR_PWR_2 = [
        lambda e, pwr_file: "Failed to load power config file '{}'. \n {}".format(
            pwr_file, e
        )
    ]

    # Memory map generator error messages
    ERR_MMAP_0 = [
        lambda e: "Key error: Sub-block '{}' should contain exactly one of (Key->'reg_map' or Key->'regions')".format(
            e
        )
    ]
    ERR_MMAP_1 = [
        lambda e: "Missing key: File '{}' has no Key->'regions' defined at top most level".format(
            e
        )
    ]
    ERR_MMAP_2 = [
        lambda e: "Invalid file: File '{}' is not a valid YAML file".format(e)
    ]
    ERR_MMAP_3 = [lambda e: "Invalid file: File '{}' is not a valid RDL file".format(e)]
    ERR_MMAP_4 = [lambda e: "Invalid file: '{}' not found.".format(e)]
    ERR_MMAP_5 = [lambda e: "ORDT returned the following error(s): \n{}".format(e)]
    ERR_MMAP_6 = [
        lambda filename: "Invalid file: ({}) is not a C header file or has an invalid path.".format(
            filename
        )
    ]
    ERR_MMAP_7 = [lambda env_var: "Envivonment variable(s) used but not defined in path ({})".format(env_var)]

    ERR_SYN_0 = [lambda: "Missing runcode parameter"]
    ERR_SYN_1 = [
        lambda runcode: "Cannot open {} runcode directory. It doesn't exist".format(
            runcode
        )
    ]
    ERR_SYN_2 = [
        lambda runcode: "Directory runcode {} already exists. Use --force swith if you want to re-write it".format(
            runcode
        )
    ]

    ERR_STA_0 = [lambda: "Missing runcode parameter"]
    ERR_STA_1 = [
        lambda runcode: "Cannot open {} runcode directory. It doesn't exist".format(
            runcode
        )
    ]
    ERR_STA_2 = [
        lambda runcode: "Directory runcode {} already exists. Use --force swith if you want to re-write it".format(
            runcode
        )
    ]
    ERR_STA_3 = [
        lambda source: "Source --source {} is not matching flow_dirs".format(source)
    ]
    ERR_STA_4 = [lambda netlist: "Netlist {} was not found".format(netlist)]
    ERR_STA_5 = [lambda mode: "Mode {} was not found".format(mode)]
    ERR_STA_6 = [lambda: "Either --dmsa or --mode <mode_name> must be used."]
    ERR_STA_7 = [lambda: "Switch --open-result shall not be used with --dmsa switch."]

    # DFT error messages
    ERR_DFT_0 = [lambda: "Missing runcode parameter"]
    ERR_DFT_1 = [
        lambda runcode: "Cannot open {} runcode directory. It doesn't exist".format(
            runcode
        )
    ]
    ERR_DFT_2 = [
        lambda runcode: "Directory runcode {} already exists. Use --force swith if you want to re-write it".format(
            runcode
        )
    ]
    ERR_DFT_3 = [lambda: "DFT root_dir cannot be selected properly."]
    ERR_DFT_4 = [lambda netlist: "Netlist {} was not found".format(netlist)]
    ERR_DFT_5 = [lambda: "Missing dft constraint file"]

    # PNR error messages
    ERR_PNR_0 = [lambda: "Missing runcode parameter"]
    ERR_PNR_1 = [
        lambda runcode: "Cannot open {} runcode directory. It doesn't exist".format(
            runcode
        )
    ]
    ERR_PNR_2 = [
        lambda runcode: "Directory runcode {} already exists. Use --force swith if you want to re-write it".format(
            runcode
        )
    ]
    ERR_PNR_3 = [
        lambda source: "Source --source {} is not matching flow_dirs".format(source)
    ]
    ERR_PNR_4 = [lambda netlist: "Netlist {} was not found".format(netlist)]


####################################################################################################
# Warning codes
####################################################################################################
class TsWarnCode(LogEnum):
    """
    List of available warning codes
    """

    # Generic warning
    GENERIC = [lambda string: str(string)]

    # Config file warnings
    WARN_CFG_1 = [
        lambda key, def_val: "Key '{}' not defined in simulation configuration file. "
        "Assuming '{}' by default.".format(key, def_val)
    ]

    # PDK / Design config file warnings
    WARN_PDK_1 = [lambda: "Design config file not found -> Skipping initialization."]
    WARN_PDK_2 = [
        lambda corner, obj: "'{}' corner for '{}' not defined!".format(corner, obj)
    ]
    WARN_PDK_3 = [
        lambda name, version, view: "'{}({})' is missing view '{}', not exporting.".format(
            name, version, view
        )
    ]
    WARN_PDK_4 = [
        lambda name, version, view, corner: "'{}({})' is missing view '{}' for corner: '{}', not exporting.".format(
            name, version, view, corner
        )
    ]
    WARN_PDK_5 = [lambda: "Floorplan not defined, but export attempted!"]
    WARN_PDK_6 = [
        lambda: "No views added, skipping TCL export. Use '--add-views=<views>' to define which views you would like to export"
    ]
    WARN_PDK_7 = [lambda: "Map file is not defined, but export attempted!"]
    WARN_PDK_8 = [lambda: "Spef file is not defined, but export attempted!"]
    WARN_PDK_9 = [lambda: "Tlu+ file is not defined, but export attempted!"]
    WARN_PDK_10 = [lambda: "RC corner is not defined, but export attempted!"]
    WARN_PDK_11 = [lambda: "Flow dirs are not defined, but export attempted!"]

    # Memory map generator warnings
    WARN_MMAP_0 = [lambda name: "Found new memory sub-region: {}".format(name)]
    WARN_MMAP_1 = [lambda name: "Parent region: {}".format(name)]


####################################################################################################
# Information codes
####################################################################################################
class TsInfoCode(LogEnum):
    """
    List of available informational codes
    """

    # Generic info
    GENERIC = [lambda string: str(string)]

    # General info messages
    INFO_CMN_0 = [
        lambda file_name: "Loading simulation configuration file: '{}'".format(
            file_name
        )
    ]
    INFO_CMN_1 = [lambda: "Checking simulation configuration..."]
    INFO_CMN_2 = [lambda: "Simulation Configuration OK!"]
    INFO_CMN_3 = [lambda tgt: "Loading source list files for target: '{}'".format(tgt)]
    INFO_CMN_5 = [lambda lib: "Compiling files for library: '{}'".format(lib)]
    INFO_CMN_13 = [lambda tests: "Tests to be executed: {}".format(", ".join(tests))]
    INFO_CMN_22 = [lambda file_name: "Compiling file: {}".format(file_name)]
    INFO_CMN_23 = [lambda: "Running recompilation before simulation! "]
    INFO_CMN_25 = [
        lambda tgt: "Loading source list files from dependent target: '{}'".format(tgt)
    ]
    INFO_CMN_26 = [lambda file_names: "Compiling files: {}".format(file_names)]

    # Hook info messages
    INFO_HOK_0 = [lambda hook_name: "Calling hook: '{}'".format(hook_name)]
    INFO_HOK_1 = [lambda hook_name: "Skipping unspecified hook: '{}'".format(hook_name)]

    # PDK config info messages
    INFO_PDK_0 = [lambda path: "Loading PDK configuration file: '{}'".format(path)]
    INFO_PDK_1 = [lambda path: "Loading Design configuration file: '{}'".format(path)]
    INFO_PDK_2 = [lambda: "Checking design configuration..."]
    INFO_PDK_3 = [lambda: "Design configuration OK!"]
    INFO_PDK_4 = [lambda pdk_name: "Loading PDK: {}".format(pdk_name)]
    INFO_PDK_5 = [lambda file: "Exporting design configuration to: '{}'".format(file)]

    # PWR info messages
    INFO_PWR_0 = [lambda path: "Loading Power configuration file: '{}'".format(path)]

    # Memory map generator error messages
    INFO_MMAP_0 = [
        lambda start_addr, end_addr: "with start address: {} and end address: {}".format(
            start_addr, end_addr
        )
    ]

    # Syn flow info messages
    INFO_SYS_0 = [lambda runcode: "Selected runcode is: {}".format(runcode)]
    INFO_SYS_1 = [lambda runcode: "Opening synthesis database: {}".format(runcode)]
    INFO_SYS_2 = [
        lambda runcode: "Deleting and creating new synthesis database: {}".format(
            runcode
        )
    ]
    INFO_SYS_3 = [
        lambda tool_type, cmd: "Following {} cmd to be executed: {}".format(
            tool_type, cmd
        )
    ]
    INFO_SYS_4 = [lambda folder: "Creating folder: {}".format(folder)]
    INFO_SYS_5 = [lambda folder: "Deleting folder: {}".format(folder)]

    # STA flow info messages
    INFO_STA_0 = [lambda runcode: "Selected runcode is: {}".format(runcode)]
    INFO_STA_1 = [lambda runcode: "Opening sta database: {}".format(runcode)]
    INFO_STA_2 = [
        lambda runcode: "Deleting and creating new sta database: {}".format(runcode)
    ]
    INFO_STA_3 = [
        lambda tool_type, cmd: "Following {} cmd to be executed: {}".format(
            tool_type, cmd
        )
    ]
    INFO_STA_4 = [lambda folder: "Creating folder: {}".format(folder)]
    INFO_STA_5 = [lambda folder: "Deleting folder: {}".format(folder)]

    # DFT flow messages
    INFO_DFT_0 = [lambda runcode: "Selected runcode is: {}".format(runcode)]
    INFO_DFT_1 = [lambda runcode: "Opening DFT database: {}".format(runcode)]
    INFO_DFT_2 = [
        lambda runcode: "Deleting and creating new DFT database: {}".format(runcode)
    ]
    INFO_DFT_3 = [
        lambda tool_type, cmd: "Following {} cmd to be executed: {}".format(
            tool_type, cmd
        )
    ]
    INFO_DFT_4 = [lambda folder: "Creating folder: {}".format(folder)]
    INFO_DFT_5 = [lambda folder: "Deleting folder: {}".format(folder)]

    # PNR flow info messages
    INFO_PNR_0 = [lambda runcode: "Selected runcode is: {}".format(runcode)]
    INFO_PNR_1 = [lambda runcode: "Opening PnR database: {}".format(runcode)]
    INFO_PNR_2 = [
        lambda runcode: "Deleting and creating new PnR database: {}".format(runcode)
    ]
    INFO_PNR_3 = [
        lambda tool_type, cmd: "Following {} cmd to be executed: {}".format(
            tool_type, cmd
        )
    ]
    INFO_PNR_4 = [lambda folder: "Creating folder: {}".format(folder)]
    INFO_PNR_5 = [lambda folder: "Deleting folder: {}".format(folder)]


def __ts_process_log(code: LogEnum, *opt_args):
    """
    Processes info/warning/error level code.
    :param code: info/warning/error code
    :param opt_args: Optional arguments passed to error code lambda function
    """
    choices = {
        TsInfoCode: logging.info,
        TsWarnCode: logging.warning,
        TsErrCode: logging.error,
    }

    try:
        choices[type(code)](code(*opt_args))
    except KeyError:
        ts_script_bug(
            "Logging code {} - type {} - is invalid, shall be one of the following types: {}".format(
                code, type(code), ", ".join(map(str, choices.keys()))
            )
        )
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
    ts_print(
        "Traceback",
        *traceback.format_stack(),
        "!! This a bug in scripting system. Report issue to developers !!",
        sep="\n",
        color=TsColors.RED,
    )
    sys.exit(2)


def ts_configure_logging(args):
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
