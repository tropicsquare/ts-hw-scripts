# -*- coding: utf-8 -*-

####################################################################################################
# Functions to support ts_pwr_run.py
#
# TODO: License
####################################################################################################

import logging
import os
import re
from datetime import datetime
import shutil

from .ts_hw_common import (
    get_repo_root_path,
    load_yaml_file,
    ts_get_root_rel_path,
    ts_get_test_dir,
    ts_set_cfg,
    ts_set_env_var,
    ts_rmdir,
    exec_cmd_in_dir
)
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsColors,
    TsErrCode,
    TSFormatter,
    TsInfoCode,
    TsWarnCode,
    ts_debug,
    ts_info,
    ts_print,
    ts_script_bug,
    ts_throw_error,
    ts_warning,
)

CORNER_DICT = {"bc": "TLUP_MIN_-40", "tc": "TLUP_TYP_25", "wc": "TLUP_MAX_125"}

RUNCODE_RESULTS_DIR = "results"
RUNCODE_FILE_PREFIX = "write_data"

def check_path (path: str):
    if not os.path.exists(path):
        ts_throw_error(TsErrCode.GENERIC, f"Path {path} does not exists!")


def load_pwr_config_file(pwr_cfg_path: str):
    """
    Loads power config file.
    :param pwr_cfg_path: Path to the config file.
    :return: Power config dictionary.
    """
    ts_debug("Loading power config file: {}".format(pwr_cfg_path))
    cfg = load_yaml_file(pwr_cfg_path)
    return cfg


def ts_get_pwr_cfg(cfg_key=None):
    """
    Access power config dictionary with some checks.
    :param cfg_key: Key.
    :return: List item.
    """
    if cfg_key is None:
        return TsGlobals.TS_PWR_CFG

    try:
        return TsGlobals.TS_PWR_CFG[cfg_key]
    except KeyError:
        ts_debug(TsGlobals.TS_PWR_CFG)
        ts_script_bug(f"Invalid key '{cfg_key}' to get in global configuration")


def ts_get_available_pwr_scenarios():
    """
    Gets names of all available power scenarios.
    :return: List of names.
    """
    ret_val = []
    for s in ts_get_pwr_cfg("scenarios"):
        ret_val.append(s)
    return ret_val

def ts_get_available_pwr_scenarios_names():
    ret_val = []
    for s in ts_get_pwr_cfg("scenarios"):
        ret_val.append(s["name"])
    return ret_val

def ts_print_available_scenarios():
    ts_print("*" * 80, color=TsColors.PURPLE)
    ts_print("Available scenarios:", color=TsColors.PURPLE)
    for s in ts_get_pwr_cfg("scenarios"):
        ts_print("    {}".format(s["name"]), color=TsColors.PURPLE)
    ts_print("*" * 80, color=TsColors.PURPLE)


def create_scenario_run_dirs(args):
    for s in TsGlobals.TS_PWR_RUN_SCENARIOS:
        if os.path.exists(s["rundir"]):
            if args.force:
                ts_info(TsInfoCode.GENERIC,
                    "Recreating directory '{}' for scenario '{}'.".format(s["rundir"], s["name"]))
                ts_rmdir(s["rundir"])
            else:
                ts_throw_error(TsErrCode.GENERIC,
                    "Scenario {} already runed below runcode {}. Use force to override it.".format(s["name"], TsGlobals.TS_RUNCODE))
        ts_debug("Creating rundir '{}'.".format(s["rundir"]))
        os.makedirs(s["rundir"])

def find_list(lst: list, key: str, val: str):
    """
    Finds sublist in a list by value of one of its fields.
    :param lst: List to be searched.
    :param key: Key of the field to search by.
    :param val: Value of the field to find.
    :return: The sublist if found. If not, then empty list.
    """
    for x in lst:
        try:
            if x[key] == val:
                return x
        except KeyError:
            ts_debug(lst, key)
            ts_script_bug(f"Invalid key '{key}' to get in list {lst}")

    ts_debug(f"No such item with \'{key}\' : \'{val}\' found in provided list")
    return None

def get_netlist_file() -> str:
    """
    Composes path to nestlist file.
    :return: Path to netlist file regarding to runcode
    """
    path = os.path.join(
        TsGlobals.TS_RUNCODE_DIR,
        RUNCODE_RESULTS_DIR,
        f"{RUNCODE_FILE_PREFIX}.v"
    )
    check_path(path)
    return path

def get_parasitic_file(mode: dict) -> str:
    """
    Composes path to parasitic (spef) file.
    :param mode: Mode
    :return: Path to parasitic file regarding to runcode and corner.
    """

    path = os.path.join(
        TsGlobals.TS_RUNCODE_DIR,
        RUNCODE_RESULTS_DIR,
        "{}.{}.spef".format(RUNCODE_FILE_PREFIX, CORNER_DICT[mode["corner"]]),
    )
    check_path(path)
    return path

def get_vcd_file(scenario: dict, seed) -> str:
    """
    Compose path to VCD file for certain scenario dumped by simulation.
    :param scenario: Scenario for which to find VCD.
    :param seed: Seed the simulation was runned with.
    :return: Path to VCD file of the scenario.
    """
    ts_set_cfg("target", scenario["simulation_target"])
    sim_test = {"name": scenario["test_name"], "seed": seed}
    path = os.path.join(ts_get_test_dir("sim", sim_test), "inter.vcd")
    check_path(path)
    return path


def get_pdk_views_for_common_config() -> str:
    """
    Returns pdk views needed for power analysis.
    :return: Constant 'nldm_db'
    """
    return "nldm_db"


def get_scenarios_to_run(scenarios_names: list) -> list:
    """
    Creates list of scenarios to be executed from 'scenario names' passed from command line.
    Uses unix like star completion.
    :param scenarios_names: List of scenario names to be queried, may contain wild-cards.
    :return: List of scenarios.
    """
    scenario_list = []
    s_cnt_prev = 0

    for scenario_name in scenarios_names:
        regex_pat = str("^" + scenario_name.replace('*', '.*') + "$")
        ts_debug(f"Test regex: {regex_pat}")
        for available_scenario in ts_get_available_pwr_scenarios():
            if re.match(regex_pat, available_scenario["name"]):
                scenario_list.append(available_scenario)
                ts_debug("Adding scenario \'{}\' to scenario list.".format(available_scenario["name"]))
        if s_cnt_prev == len(scenario_list):
            ts_throw_error(TsErrCode.GENERIC,
                "Specified scenario {} does not match any available scenario.\nUse --list-scenarios.".format(scenario_name))
        else:
            s_cnt_prev = len(scenario_list)

    return scenario_list


def xterm_cmd_wrapper (cmd: str) -> str:
    """
    Wraps a command to be used with xterm"
    :param cmd: Command to be wrapped.
    :return: Wrapped command.
    """
    mod_cmd = cmd.replace('"', '\\"')
    return f"TERM=xterm /usr/bin/bash -c \"{mod_cmd}\""


def build_run_sim_cmd(scenario: dict, seed: int, args):
    """
    Builds command to run simulation.
    :param scenario: Power scenario.
    :param seed: Seed for simulation.
    :param args: args.
    :return: Builded command
    """
    ts_debug("Building simulation command.")
    ts_sim_run_args = "{}".format(scenario["simulation_target"])
    ts_sim_run_args += " {}".format(scenario["test_name"])

    ts_sim_run_args += " --dump-waves"

    if args.recompile:
        ts_sim_run_args += " --recompile"

    if args.clear_sim:
        ts_sim_run_args += " --clear"

    if args.clear_sim_logs:
        ts_sim_run_args += " --clear-logs"

    if args.license_wait:
        ts_sim_run_args += " --license-wait"

    ts_sim_run_args += " --seed {}".format(seed)

    ts_sim_run_args += ' --add-elab-options "'
    ts_sim_run_args += "+vcs+dumpvars+inter.vcd"
    ts_sim_run_args += " +vcs+dumpon+{}000".format(scenario["from"])
    ts_sim_run_args += " +vcs+dumpoff+{}000".format(scenario["to"])
    ts_sim_run_args += '"'

    return f"ts_sim_run.py {ts_sim_run_args}"


def build_design_cfg_cmd(export_path: str):
    """
    Builds command to export common design config file
    :param export_path: path where the file shall be exported
    :return: command tu run
    """
    ts_design_cfg_args = f" --exp-tcl-design-cfg {export_path}"
    ts_design_cfg_args += f" --add-views={get_pdk_views_for_common_config()}"
    ts_design_cfg_args += " --add-top-entity"

    return f"ts_design_cfg.py {ts_design_cfg_args}"


def build_prime_time_cmd(scenario):
    """
    Builds command to run power analysis
    :return: command tu run
    """
    pt_shell_cmd_args = "-f {}".format(TsGlobals.TS_PWR_RUN_FILE)
    log_file = os.path.join(scenario["rundir"], "pt_shell.log")
    pt_shell_cmd_args += f" -output_log_file {log_file}"

    set_args = "set RUNCODE_DIR {}; ".format(TsGlobals.TS_PWR_RUNCODE_DIR)
    set_args += "set SCENARIO {} ".format(scenario["name"])
    pt_shell_cmd_args += f" -x \"{set_args}\""

    return f"pt_shell {pt_shell_cmd_args}"


def generate_pre_pwr_hook(scenario, args):
    """
    Generates pre-PrimeTime hook.
    :param scenario: Scenario for which to generate it.
    :args: args
    """
    path = os.path.join(scenario["rundir"], "pre_hook.tcl")
    prehook_file = open(path, 'w')

    lines = []

    lines.append("##############################################\n")
    lines.append("# PrimeTime Pre-Hook file\n")
    lines.append("# Generated automatically by ts-hw-scripts\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append('puts "RM-Info: Running script [info script]"\n')
    lines.append("\n")

    prehook_file.writelines(lines)
    prehook_file.close()


def generate_post_pwr_hook(scenario, args):
    """
    Generates post-PrimeTime hook.
    :param scenario: Scenario for which to generate it.
    :args: args
    """
    path = os.path.join(scenario["rundir"], "post_hook.tcl")
    posthook_file = open(path, 'w')

    lines = []

    lines.append("##############################################\n")
    lines.append("# PrimeTime Post-Hook file\n")
    lines.append("# Generated automatically by ts-hw-scripts\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append('puts "RM-Info: Running script [info script]"\n')
    lines.append("\n")

    if not args.stay_in_tool:
        lines.append("exit")
        lines.append("\n")

    posthook_file.writelines(lines)
    posthook_file.close()


def generate_common_setup():
    """
    Generates common setup.
    """
    ts_info(TsInfoCode.GENERIC, "Generating common setup.")
    path = os.path.join(TsGlobals.TS_PWR_RUNCODE_DIR, "common_setup.tcl")
    design_cfg_cmd = xterm_cmd_wrapper(build_design_cfg_cmd(path))
    ts_debug(f"Running command {design_cfg_cmd}")
    exec_cmd_in_dir(
        directory=TsGlobals.TS_PWR_RUNCODE_DIR,
        command=design_cfg_cmd,
        batch_mode=False
    )

def generate_scenario_setup(scenario: dict, vcd_file: str, args):
    """
    Generates specific power setup for scenario.
    :param scenario: Scenario for which to generate it.
    """
    ts_info(TsInfoCode.GENERIC, "Generating power setup.")

    path = os.path.join(scenario["rundir"], "scenario_setup.tcl")

    # Create and open the setup file
    setup_file = open(path, "w")

    lines = []

    lines.append("##############################################\n")
    lines.append("# PrimeTime Variables setup file\n")
    lines.append("# Generated automatically by ts-hw-scripts\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append('puts "RM-Info: Running script [info script]"\n')
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Report and Result Directories\n")
    lines.append("##############################################\n")
    lines.append("set REPORTS_DIR \"{}/reports\"\n".format(scenario["rundir"]))
    lines.append("set RESULTS_DIR \"{}/results\"\n".format(scenario["rundir"]))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Library and Design Setup\n")
    lines.append("##############################################\n")
    lines.append("set search_path     \". $TS_NLDM_DB_VIEW_DIRS $search_path\"\n")
    lines.append("set target_library  [dict get $TS_NLDM_DB_VIEWS {}]\n".format(scenario["mode"]["name"].upper()))
    lines.append("set link_path       \"* $target_library\"\n")
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Waves Dumping Setup\n")
    lines.append("##############################################\n")
    if args.dump_pwr_waves:
        lines.append("set WAVEFORM_FORMAT {}\n".format(args.dump_pwr_waves))
    else:
        lines.append("set WAVEFORM_FORMAT none\n")
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Netlist Setup\n")
    lines.append("##############################################\n")
    lines.append('set NETLIST_FILES "{}"\n'.format(get_netlist_file()))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Non-DMSA Power Analysis Setup Section\n")
    lines.append("##############################################\n")
    lines.append("set ACTIVITY_FILE \"{}\"\n".format(vcd_file))
    lines.append("set STRIP_PATH \"{}\"\n".format(TsGlobals.TS_PWR_CFG["strip_path"]))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Back Annotation File Section\n")
    lines.append("##############################################\n")
    lines.append("set PARASITIC_FILE \"{}\"\n".format(get_parasitic_file(scenario["mode"])))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Constraint Section Setup\n")
    lines.append("##############################################\n")
    lines.append("set CONSTRAINT_FILE \"{}\"\n".format(scenario["mode"]["constraints"]))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# End\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append('puts "RM-Info: Completed script [info script]"\n')

    setup_file.writelines(lines)
    setup_file.close()


def extend_pwr_cfg():
    """
    Extends TsGlobals.TS_PWR_CFG by rundir and mode for each scenario
    """
    for s in TsGlobals.TS_PWR_CFG["scenarios"]:
        s["rundir"] = os.path.join(TsGlobals.TS_PWR_RUNCODE_DIR, s["name"])
        s["mode"] = find_list(TsGlobals.TS_DESIGN_CFG["design"]["modes"], "name", s["mode"])


def set_runcode(args):
    """
    Checks and sets runcode.
    """
    try:
        TsGlobals.TS_RUNCODE = os.environ["TS_RUNCODE"]
    except KeyError:
        ts_warning(TsWarnCode.GENERIC, "Environment variable TS_RUNCODES is not set.")

    if hasattr(args, "runcode") and args.runcode != None:
        ts_info(TsInfoCode.GENERIC, f"Overriding defautl runcode with {args.runcode}")
        TsGlobals.TS_RUNCODE = args.runcode

    if TsGlobals.TS_RUNCODE is None:
        ts_throw_error(TsErrCode.GENERIC, "No runcode specified or previously defined! Exiting.\n")
    else:
        ts_info(TsInfoCode.GENERIC, f"Runcode for power analysis: {TsGlobals.TS_RUNCODE}")


def set_pwr_runcode_dir():
    try:
        TsGlobals.TS_PWR_RUNCODE_DIR = ts_get_root_rel_path(
            os.path.join(TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["pwr"],
            TsGlobals.TS_RUNCODE)
        )
    except KeyError:
        ts_throw_error(TsErrCode.GENERIC, "No pwr directory specified.")


def set_pwr_env(args):

    set_pwr_runcode_dir()
    extend_pwr_cfg()
    check_scenario_args()

    if os.path.exists(TsGlobals.TS_PWR_RUNCODE_DIR) and not args.force and args.add_scenario is None:
        ts_throw_error(TsErrCode.GENERIC,
            f"Power analysis for runcode {TsGlobals.TS_RUNCODE} already done, plese use --force.")

    if args.force and args.add_scenario is None:
        ts_info(TsInfoCode.GENERIC, f"Forced to re-run runcode {TsGlobals.TS_RUNCODE}.")
        ts_rmdir(TsGlobals.TS_PWR_RUNCODE_DIR)
        os.makedirs(TsGlobals.TS_PWR_RUNCODE_DIR)

    if args.add_scenario == "all" or args.add_scenario is None:
        scenarios_names = ["*"]
    else:
        scenarios_names = args.add_scenario.split(',')

    TsGlobals.TS_PWR_RUN_SCENARIOS = get_scenarios_to_run(scenarios_names)
    create_scenario_run_dirs(args)


def check_pwr_args(args):
    """
    Checks if arguments make sense.
    :param args: args.
    """
    try:
        TsGlobals.TS_RUNCODE_DIR = os.path.join(TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]["pnr"], TsGlobals.TS_RUNCODE)
        check_path(TsGlobals.TS_RUNCODE_DIR)
    except KeyError:
        ts_throw_error(TsErrCode.GENERIC, "No pnr directory specified.")


def check_scenario_args():
    for s in TsGlobals.TS_PWR_CFG["scenarios"]:
        ts_debug("Checking args for scenario {}".format(s["name"]))
        if "constraints" not in s["mode"].keys():
            ts_throw_error(TsErrCode.GENERIC,
                "No SDC file specified for mode '{}'.".format(s['mode']['name'])
            )

def check_primetime_run_script():
    if not os.path.exists(TsGlobals.TS_PWR_RUN_FILE):
        ts_throw_error(
            TsErrCode.GENERIC,
            f"PrimeTime run script {TsGlobals.TS_PWR_RUN_FILE} does not exists!",
        )


def get_pwr_waves_path(scenario):
    """
    Gets path to power waves.
    """
    path = os.path.join(scenario["rundir"], "reports", "wave.fsdb")
    check_path(path)
    return path


def get_optional_key(dictionary: dict, key: str):
    """
    Gets value of item by key that is optional in dictionary.
    :return: Value of the item, if present, False otherwise.
    """
    if key in dictionary.keys():
        return dictionary[key]
    else:
        return False


def set_prime_time_license_queuing(enable: bool):
    """
    Enables/Disables license queuing for PrimeTime
    :param enable: bool
    """
    if enable:
        ts_info(TsInfoCode.GENERIC, "Enabling PrimeTime license queuing.")
        ts_set_env_var("SNPSLMD_QUEUE", "true")
    else:
        ts_info(TsInfoCode.GENERIC, "Disabling PrimeTime license queuing.")
        ts_set_env_var("SNPSLMD_QUEUE", "false")


def set_verdi_license_queuing(enable: bool):
    """
    Enables/Disables license queuing for Verdi
    :param enable: bool
    """
    if enable:
        ts_info(TsInfoCode.GENERIC, "Enabling Verdi license queuing.")
        ts_set_env_var("NOVAS_LICENSE_QUEUE", "1")
    else:
        ts_info(TsInfoCode.GENERIC, "Disabling Verdi license queuing.")
        ts_set_env_var("NOVAS_LICENSE_QUEUE", "0")


def pwr_logging(args):
    """
    Configures additional handler for logging power flow file log
    """
    # Get existing logger
    logger = logging.getLogger()
    # Create time stamp for a log file name
    now = datetime.now().strftime("%Y%m%d.%H%M")
    # Set full path and a name of the log file
    logs_dir = "{}/pwr/logs".format(get_repo_root_path())
    os.makedirs(logs_dir, exist_ok=True)
    filename = "{}/power_{}_{}.log".format(logs_dir, args.runcode, now)
    handler = logging.FileHandler(filename)
    handler.setFormatter(TSFormatter(use_colors=False))
    logger.addHandler(handler)


def restore_pwr_session(args) -> int:
    set_pwr_runcode_dir()

    if args.restore not in ts_get_available_pwr_scenarios_names():
        ts_throw_error(TsErrCode.GENERIC, "Specified scenario does not exists in power config file.")

    scenario_dir_path = os.path.join(TsGlobals.TS_PWR_RUNCODE_DIR, args.restore)
    session_path = os.path.join(scenario_dir_path, os.environ["TS_DESIGN_NAME"]+"_ss")

    check_path(session_path)

    cmd = xterm_cmd_wrapper(f"pt_shell -x \"restore_session {session_path}\"")
    ts_debug(f"Running command {cmd}")
    return_code = exec_cmd_in_dir(
        directory=scenario_dir_path,
        command=cmd,
        batch_mode=args.batch_mode
    )

    return return_code


def open_pwr_waves(args):
    set_pwr_runcode_dir()

    if args.open_pwr_waves not in ts_get_available_pwr_scenarios_names():
        ts_throw_error(TsErrCode.GENERIC, "Specified scenario does not exists in power config file.")

    scenario_dir_path = os.path.join(TsGlobals.TS_PWR_RUNCODE_DIR, args.open_pwr_waves)
    waves_path = os.path.join(scenario_dir_path, "reports",  os.environ["TS_DESIGN_NAME"]+"_wave.fsdb")

    check_path(waves_path)

    cmd = f"verdi -sx {waves_path}"
    ts_debug(f"Running command {cmd}")
    return_code = exec_cmd_in_dir(
        directory=scenario_dir_path,
        command=cmd,
        batch_mode=args.batch_mode
    )

    return return_code
