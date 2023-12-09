# -*- coding: utf-8 -*-

####################################################################################################
# Configuration file parser and over-riding by script options
#
# For license see LICENSE file in repository root.
####################################################################################################

import copy
import os
import re

from schema import SchemaError

from .ts_grammar import GRAMMAR_DSG_CONFIG, GRAMMAR_PWR_CONFIG, GRAMMAR_SIM_CFG
from .ts_hw_common import (
    check_target,
    expand_vars,
    load_yaml_file,
    ts_get_cfg,
    ts_get_curr_dir_rel_path,
    ts_get_root_rel_path,
    ts_set_cfg,
)
from .ts_hw_design_config_file import (
    filter_design_config_file,
    load_design_config_file,
    load_pdk_configs,
    validate_design_config_file,
)
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsErrCode,
    TsInfoCode,
    TsWarnCode,
    ts_debug,
    ts_info,
    ts_print,
    ts_script_bug,
    ts_throw_error,
    ts_warning,
)
from .ts_hw_pwr_support import load_pwr_config_file, ts_get_pwr_cfg
from .ts_hw_test_list_files import check_test, load_tests


def fill_default_config_regress_values(cfg_curr: dict):
    """
    Fills default values for ts_sim_regress run which are filled by argparse in ts_sim_run.py
    """
    cfg_curr.update(
        {
            "add_sim_options": "",
            "add_elab_options": "",
            "clear_logs": False,
            "dump_waves": False,
            "elab_only": False,
            "fail_fast": False,
            "gui": None,
            "loop": False,
            "no_check": False,
            "no_sim_out": True,
        }
    )


def __load_sim_config_file(sim_cfg_path):
    """
    Loads simulation configuration file
    :param sim_cfg_path: Config file path
    :return: Config file YAML object
    """
    ts_debug("Loading simulation config file: {}".format(sim_cfg_path))
    cfg = load_yaml_file(sim_cfg_path)
    ts_debug("Simulation config file loaded!")
    return cfg


def __merge_args_with_config(args):
    """
    Merges command line arguments with loaded configuration from simulation config file
    Command line arguments have priority!
    :param args: Command line arguments
    """
    ts_debug("Merging config file with command line attributes")
    for attr_key in GRAMMAR_SIM_CFG.attrs():
        ts_debug("Parsing attribute: {}".format(attr_key))
        try:
            attr_val = getattr(args, attr_key)
        except AttributeError:
            ts_debug("Attribute {} not found".format(attr_key))
            continue
        ts_debug("Attribute value: {}".format(attr_val))

        # If destination attribute does not exist in the config then set it
        # This allows setting options - i.e. "verbose" - even if they are not in config file
        if attr_key not in ts_get_cfg():
            ts_set_cfg(attr_key, attr_val)
        # Override boolean attributes only if True
        # If something is enabled in sim config file, it cannot be disabled it by command line
        elif isinstance(attr_val, bool):
            if attr_val is True:
                ts_set_cfg(attr_key, attr_val)
        # If string attributes are set, override them
        elif isinstance(attr_val, str):
            if attr_val != "":
                ts_set_cfg(attr_key, attr_val)


def __finalize_config():
    """
    Perform additional actions to complete the configuration.
    """
    ts_debug("Expanding environment variables of TS_SIM_CFG")
    TsGlobals.TS_SIM_CFG = expand_vars(TsGlobals.TS_SIM_CFG)

    ts_debug("Resolving targets inheritance")

    def __inherit_dict(parent_dict, child_dict):
        result_dict = copy.deepcopy(parent_dict)
        for key, val in child_dict.items():
            if key in result_dict:
                if isinstance(val, dict):
                    result_dict[key].update(val)
                elif isinstance(val, list):
                    result_dict[key].extend(val)
                else:
                    result_dict[key] = val
            else:
                result_dict[key] = val
        return result_dict

    _MAX_INHERITANCE_LEVEL = 5

    def _solve_inheritance(target, level=0):
        if level > _MAX_INHERITANCE_LEVEL:
            raise RecursionError(
                f"Exceeded maximum inheritance level: {_MAX_INHERITANCE_LEVEL}"
            )
        if "inherits" in TsGlobals.TS_SIM_CFG["targets"][target]:
            _solve_inheritance(
                TsGlobals.TS_SIM_CFG["targets"][target]["inherits"], level + 1
            )
            TsGlobals.TS_SIM_CFG["targets"][target] = __inherit_dict(
                TsGlobals.TS_SIM_CFG["targets"][
                    TsGlobals.TS_SIM_CFG["targets"][target]["inherits"]
                ],
                TsGlobals.TS_SIM_CFG["targets"][target],
            )
            del TsGlobals.TS_SIM_CFG["targets"][target]["inherits"]

    for target in TsGlobals.TS_SIM_CFG.get("targets", []):
        _solve_inheritance(target)


def __check_sim_config():
    """
    Checks simulation config file for validity.
    Throws an exception if config file has an error in it.
    """
    ts_debug("Checking configuration against grammar template")
    try:
        TsGlobals.TS_SIM_CFG = GRAMMAR_SIM_CFG.validate(TsGlobals.TS_SIM_CFG)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_CFG_23, e)

    ts_debug("Performing additional checks")

    ts_debug("Checking test strategy parameters")
    for to_test in (TsGlobals.TS_SIM_CFG, *TsGlobals.TS_SIM_CFG["targets"].values()):
        if to_test.get("test_name_strategy") == "generic_parameter":
            if (
                to_test.get("test_name_generic"),
                to_test.get("test_name_parameter"),
            ) == (None, None):
                ts_throw_error(TsErrCode.ERR_CFG_22)

    ts_debug("Checking coupling of 'ignore_start' and 'ignore_stop' patterns")
    config_keys = set(TsGlobals.TS_SIM_CFG.keys())
    for kwd_pair in (
        {"error_ignore_start", "error_ignore_stop"},
        {"warning_ignore_start", "warning_ignore_stop"},
    ):
        # start and stop cannot be one without the other
        if len(kwd_pair - config_keys) == 1:
            ts_throw_error(TsErrCode.ERR_CFG_13, *kwd_pair)


def __check_design_config():
    """ """
    try:
        TsGlobals.TS_DESIGN_CFG = GRAMMAR_DSG_CONFIG.validate(TsGlobals.TS_DESIGN_CFG)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_PDK_2, e)


def do_sim_config_init(args, skip_check=False):
    """
    Common initialization for all scripts which load simulation config files.
    Performs following:
        1. Loads simulation config file
        2. Merges simulation config files with command line arguments
        3. Checks if configs are valid (no invalid keywords, or values).
    :param args: Command line arguments
    """
    # Loading simulation config
    ts_info(TsInfoCode.INFO_CMN_0, TsGlobals.TS_SIM_CFG_PATH)

    try:
        TsGlobals.TS_SIM_CFG = __load_sim_config_file(
            ts_get_curr_dir_rel_path(args.sim_cfg)
        )
    except AttributeError:
        ts_script_bug(
            "Command line arguments shall have 'sim_cfg' defined "
            "either explicitly or by default value!"
        )

    ts_debug(f"Simulation config file: {ts_get_cfg()}")

    # Merging command line arguments with config file
    __merge_args_with_config(args)
    ts_debug(
        "Simulation configuration (merged config file and command-line arguments):"
    )
    ts_debug(ts_get_cfg())

    # Finalize configuration
    __finalize_config()

    if skip_check:
        ts_debug("Skipping configuration check.")
        return

    # Checking simulation config file
    ts_info(TsInfoCode.INFO_CMN_1)
    __check_sim_config()
    ts_info(TsInfoCode.INFO_CMN_2)


def do_design_config_init(args, skip_check=False, enforce=False):
    """ """
    # Load Design config file
    cfg_file_path = ts_get_curr_dir_rel_path(args.design_cfg)
    ts_info(TsInfoCode.INFO_PDK_1, cfg_file_path)
    try:
        if os.path.exists(cfg_file_path):
            TsGlobals.TS_DESIGN_CFG = load_design_config_file(cfg_file_path)
        else:
            if enforce:
                ts_throw_error(TsErrCode.ERR_PDK_24, cfg_file_path)
            else:
                ts_warning(TsWarnCode.WARN_PDK_1)
            return
    except Exception as e:
        ts_throw_error(TsErrCode.ERR_PDK_1, e, cfg_file_path)

    # Check towards grammar
    if not skip_check:
        ts_info(TsInfoCode.INFO_PDK_2)
        __check_design_config()
        ts_info(TsInfoCode.INFO_PDK_3)

    # Read in PDKS
    load_pdk_configs()

    # Check that Design config is valid (it references towards PDK objects)
    validate_design_config_file()

    # Remove filtered design modes objects
    filter_design_config_file(args)


def do_lint_init(args):
    """
    Returns do_lint_init fuction based on selected tool

    """
    # Example TsGlobals.TS_DFT_LINT_TOOL
    types = f"TsGlobals.TS_{args.flow.upper()}_TOOL"
    # Example do_dft_lint_spyglass_init
    cmd = f"do_{args.flow}_{eval(types)}_init(args)"
    try:
        return eval(cmd)
    except KeyError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Not defined ts_hw_cfg_parser.do_{args.flow}_{TsGlobals.TS_DFT_LINT_TOOL}_init() for selected LINT tool {TsGlobals.TS_DFT_LINT_TOOL}",
        )


def do_rtl_lint_spyglass_init(args):
    """
    Spyglass constraints selection
        :args :lint_constraints - relative/absoluth path + name of the file *.sgdc
              :mode             - name in accordance with design_cfg modes
    """
    if args.open_result is True:
        return

    if args.lint_constraints is None and args.mode is None:
        ts_throw_error(TsErrCode.ERR_DFT_5)
    else:
        file_path = None

        # Check existance of any constraints based on selected mode
        # the sgdc expect *dft_{args.mode}*
        if args.mode is not None:
            root_dir = ts_get_root_rel_path(f"lint/{TsGlobals.TS_RTL_LINT_TOOL}/sgdc/")
            regex = re.compile(rf"(.*)(rtl_{args.mode})(.*)(sgdc)$")

        # Check existance of selected constraints
        if args.lint_constraints is not None:
            root_dir = ts_get_root_rel_path(os.path.dirname(args.lint_constraints))
            regex = re.compile(rf"({os.path.basename(args.lint_constraints)})$")

        try:
            files = [
                f
                for f in os.listdir(root_dir)
                if os.path.isfile(os.path.join(root_dir, f))
            ]
            for f in files:
                result = regex.search(f)
                if result:
                    TsGlobals.TS_RTL_LINT_CONSTRAINT = f"{root_dir}/{result.string}"
            if TsGlobals.TS_RTL_LINT_CONSTRAINT is None:
                raise
        except:
            ts_throw_error(TsErrCode.ERR_DFT_5)


def do_dft_lint_spyglass_init(args):
    """
    Spyglass constraints selection
        :args :lint_constraints - relative/absoluth path + name of the file *.sgdc
              :mode             - name in accordance with design_cfg modes
    """
    if args.open_result is True:
        return

    if args.lint_constraints is None and args.mode is None:
        ts_throw_error(TsErrCode.ERR_DFT_5)
    else:
        file_path = None

        # Check existance of any constraints based on selected mode
        # the sgdc expect *dft_{args.mode}*
        if args.mode is not None:
            root_dir = ts_get_root_rel_path(f"lint/{TsGlobals.TS_DFT_LINT_TOOL}/sgdc/")
            if args.netlist:
                regex = re.compile(rf"(.*)(dft_{args.mode}_netlist)(.*)(sgdc)$")
            else:
                regex = re.compile(rf"(.*)(dft_{args.mode})(.*)(sgdc)$")

        # Check existance of selected constraints
        if args.lint_constraints is not None:
            root_dir = ts_get_root_rel_path(os.path.dirname(args.lint_constraints))
            regex = re.compile(rf"({os.path.basename(args.lint_constraints)})$")

        try:
            files = [
                f
                for f in os.listdir(root_dir)
                if os.path.isfile(os.path.join(root_dir, f))
            ]
            for f in files:
                result = regex.search(f)
                if result:
                    TsGlobals.TS_DFT_CONSTRAINT = f"{root_dir}/{result.string}"
            if TsGlobals.TS_DFT_CONSTRAINT is None:
                raise
        except:
            ts_throw_error(TsErrCode.ERR_DFT_5)


def __check_pwr_scenarios():
    ts_debug("Checking power scenarios.")
    scenarios = ts_get_pwr_cfg("scenarios")

    # check target and test name
    for s in scenarios:
        ts_debug(
            "Checking simulation target '{}' of scenario '{}'".format(
                s["simulation_target"], s["name"]
            )
        )
        check_target(s["simulation_target"])
        ts_set_cfg("target", s["simulation_target"])
        load_tests()
        ts_debug(
            "Checking test name '{}' of scenario '{}'".format(s["test_name"], s["name"])
        )
        check_test(s["test_name"])

    # check times
    for s in scenarios:
        ts_debug("Checking time interval for scenario '{}'".format(s["name"]))
        if s["from"] > s["to"]:
            ts_throw_error(
                TsErrCode.GENERIC,
                "Invalid time interval <{}, {}> for scenario '{}'!".format(
                    s["from"], s["to"], s["name"]
                ),
            )
        if s["from"] == s["to"]:
            ts_warning(
                TsWarnCode.GENERIC,
                "Zero time interval <{}, {}> for scenario '{}'.".format(
                    s["from"], s["to"], s["name"]
                ),
            )

    # check mode
    modes = []
    for m in TsGlobals.TS_DESIGN_CFG["design"]["modes"]:
        modes.append(m["name"])
    for s in scenarios:
        ts_debug("Checking mode '{}' for scenario '{}'".format(s["mode"], s["name"]))
        if s["mode"] not in modes:
            ts_throw_error(
                TsErrCode.GENERIC,
                "Invalid mode '{}' for scenario '{}'! Available modes: {}".format(
                    s["mode"], s["name"], modes
                ),
            )


def __check_pwr_config():
    """
    Checks power configuration.
    """
    ts_debug("Checking grammar of power config file.")
    try:
        GRAMMAR_PWR_CONFIG.validate(TsGlobals.TS_PWR_CFG)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_PWR_0, e)
    __check_pwr_scenarios()


def do_power_config_init(args, skip_check=False):
    """
    Initiate power configuration.
    """
    # Load Power config file
    cfg_file_path = ts_get_curr_dir_rel_path(args.pwr_cfg)
    if not os.path.exists(cfg_file_path):
        ts_throw_error(TsErrCode.ERR_PWR_1)

    ts_info(TsInfoCode.INFO_PWR_0, cfg_file_path)
    try:
        TsGlobals.TS_PWR_CFG = load_pwr_config_file(cfg_file_path)
    except Exception as e:
        ts_throw_error(TsErrCode.ERR_PWR_2, e, cfg_file_path)

    if not skip_check:
        ts_info(TsInfoCode.GENERIC, "Checking Power configuration file.")
        __check_pwr_config()


def check_valid_design_target():
    """ """
    if TsGlobals.TS_DESIGN_CFG["design"]["target"] not in ts_get_cfg("targets"):
        ts_throw_error(
            TsErrCode.ERR_PDK_15,
            TsGlobals.TS_DESIGN_CFG["design"]["target"],
            str(list(ts_get_cfg("targets").keys())),
        )


def print_target_list():
    """
    Prints list of available compilation/simulation targets.
    """
    ts_print("List of available targets:", *ts_get_cfg("targets"), sep="\n\t")


def check_valid_source_data_arg(args):
    """
    Check whether source_data arg matches flow_dirs attribute list
    """
    if args.source_data:
        if "flow_dirs" in TsGlobals.TS_DESIGN_CFG["design"]:
            if (
                args.source_data
                not in TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"].keys()
            ):
                ts_throw_error(TsErrCode.ERR_STA_3, args.source_data)
        else:
            ts_throw_error(TsErrCode.ERR_STA_3, args.source_data)


def check_valid_mode_arg(args):
    """
    Check whether mode arg matches modes attribute list
    """
    if args.mode:
        modes_names = []
        for i, mode in enumerate(TsGlobals.TS_DESIGN_CFG["design"]["modes"]):
            modes_names.append(mode["name"])
        if args.mode not in modes_names:
            ts_throw_error(TsErrCode.ERR_STA_5, args.mode)


def parse_runcode_arg(args):
    """
    Parses runcode with regards to defined rules by methodology.
    Test of runcode existance, _n+1 rule usage.
    """
    if args.open_result or args.force:
        return f"{args.runcode}"

    if args.runcode:
        root_dir = os.getcwd()
        result = None
        suffix = None

        regex = re.compile(rf"({args.runcode})(_*)([0-9]*)$")
        for dir in os.listdir(root_dir):
            result = regex.search(dir)
            if result:
                if suffix is None:
                    suffix = 0
                if result.group(3):
                    if suffix < int(result.group(3)):
                        suffix = int(result.group(3))

        if suffix is not None:
            return f"{args.runcode}_{suffix+1}"
        else:
            return f"{args.runcode}"
    else:
        return None


def parse_runcode_arg_root_dir(args, root_dir):
    """
    Parses runcode with regards to defined rules by methodology.
    Test of runcode existance, _n+1 rule usage.
    """
    if args.open_result or args.force:
        return f"{args.runcode}"

    if not os.path.exists(root_dir):
        return f"{args.runcode}"

    if args.runcode:
        result = None
        suffix = None

        regex = re.compile(rf"({args.runcode})(_*)([0-9]*)$")
        for dir in os.listdir(root_dir):
            result = regex.search(dir)
            if result:
                if suffix is None:
                    suffix = 0
                if result.group(3):
                    if suffix < int(result.group(3)):
                        suffix = int(result.group(3))

        if suffix is not None:
            return f"{args.runcode}_{suffix+1}"
        else:
            return f"{args.runcode}"
    else:
        return None
