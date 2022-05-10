# -*- coding: utf-8 -*-

####################################################################################################
# Configuration file parser and over-riding by script options
#
# TODO: License
####################################################################################################

import os
import copy
from schema import SchemaError

from .ts_hw_common import *
from .ts_grammar import *


def fill_default_config_regress_values(cfg_curr: dict):
    """
    Fills default values for ts_sim_regress run which are filled by argparse in ts_sim_run.py
    """
    cfg_curr.update({
        "add_sim_options": "",
        "add_elab_options": "",
        "clear_logs": False,
        "dump_waves": False,
        "elab_only": False,
        "fail_fast": False,
        "gui": None,
        "loop": False,
        "no_check": False,
        "session_file": "",
        "no_sim_out": True
    })


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
    for attr_key in GRAMMAR_SIM_CFG:
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
            raise RecursionError(f"Exceeded maximum inheritance level: {_MAX_INHERITANCE_LEVEL}")
        if "inherits" in TsGlobals.TS_SIM_CFG["targets"][target]:
            _solve_inheritance(TsGlobals.TS_SIM_CFG["targets"][target]["inherits"], level + 1)
            TsGlobals.TS_SIM_CFG["targets"][target] = __inherit_dict(
                TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_SIM_CFG["targets"][target]["inherits"]],
                TsGlobals.TS_SIM_CFG["targets"][target])
            del TsGlobals.TS_SIM_CFG["targets"][target]["inherits"]

    for target in TsGlobals.TS_SIM_CFG.get("targets", []):
        _solve_inheritance(target)


def __check_config():
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
            if (to_test.get("test_name_generic"), to_test.get("test_name_parameter")) == (None, None):
                ts_throw_error(TsErrCode.ERR_CFG_22)

    ts_debug("Checking coupling of 'ignore_start' and 'ignore_stop' patterns")
    config_keys = set(TsGlobals.TS_SIM_CFG.keys())
    for kwd_pair in ({"error_ignore_start", "error_ignore_stop"},
                    {"warning_ignore_start", "warning_ignore_stop"}):
        # start and stop cannot be one without the other
        if len(kwd_pair - config_keys) == 1:
            ts_throw_error(TsErrCode.ERR_CFG_13, *kwd_pair)


def do_config_init(args, skip_check=False):
    """
    Common initialization for all scripts which load simulation config file. Performs following:
        1. Loads simulation config file
        2. Merges simulation config file with command line arguments
        3. Checks if config is valid (no invalid keywords, or values).
    :param args: Command line arguments
    """
    # Loading simulation config
    ts_info(TsInfoCode.INFO_CMN_0, TsGlobals.TS_SIM_CFG_PATH)

    try:
        TsGlobals.TS_SIM_CFG = __load_sim_config_file(ts_get_curr_dir_rel_path(args.sim_cfg))
    except AttributeError:
        ts_script_bug("Command line arguments shall have 'sim_cfg' defined "
                        "either explicitly or by default value!")

    ts_debug(f"Simulation config file: {ts_get_cfg()}")

    # Merging command line arguments with config file
    __merge_args_with_config(args)
    ts_debug("Simulation configuration (merged config file and command-line arguments):")
    ts_debug(ts_get_cfg())

    # Finalize configuration
    __finalize_config()

    if skip_check:
        ts_debug("Skipping configuration check.")
        return

    # Checking simulation config file
    ts_info(TsInfoCode.INFO_CMN_1)
    __check_config()
    ts_info(TsInfoCode.INFO_CMN_2)


def print_target_list():
    """
    Prints list of available compilation/simulation targets.
    """
    ts_print("List of available targets:", *ts_get_cfg("targets"), sep="\n\t")

