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

from .ts_hw_common import (
    exec_cmd_in_dir,
    get_repo_root_path,
    load_yaml_file,
    ts_get_root_rel_path,
    ts_get_test_dir,
    ts_set_cfg,
    ts_set_env_var,
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
from .ts_hw_source_list_files import get_netlist_from_slf

# TODO: solve how to get to spef files from some config file and not hardcoded
# SPEF_PATH = "/projects/tropic01/pnr_export/ICC2_topo31_v1_sdc26_rev1_holdFix2/results/"
# SPEF_WC = "write_data.TLUP_MAX_125.spef"
# SPEF_TYP = "write_data.TLUP_TYP_25.spef"
# SPEF_BC = "write_data.TLUP_MIN_-40.spef"
#
# SPEF_DICT = {
#    "func_wc"   :   SPEF_WC,
#    "func_typ"  :   SPEF_TYP,
#    "func_bc"   :   SPEF_BC
# }

CORNER_DICT = {"bc": "TLUP_MIN_-40", "tc": "TLUP_TYP_25", "wc": "TLUP_MAX_125"}

RUNCODE_RESULTS_DIR = "results"
RUNCODE_FILE_PREFIX = "write_data"


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
        ts_script_bug(f"Invalid key \'{cfg_key}\' to get in global configuration")

def ts_get_available_pwr_scenarios():
    """
    Gets names of all available power scenarios.
    :return: List of names.
    """
    ret_val = []
    for s in ts_get_pwr_cfg("scenarios"):
        ret_val.append(s)
    return ret_val

def ts_print_available_scenarios():
    ts_print("*" * 80, color=TsColors.PURPLE)
    ts_print("Available scenarios:", color=TsColors.PURPLE)
    for s in ts_get_available_pwr_scenarios():
        ts_print("    {}".format(s["name"]), color=TsColors.PURPLE)
    ts_print("*" * 80, color=TsColors.PURPLE)

def check_pwr_scenario(pwr_scenario):
    """
    Checks if scenario provided scenario is available in power config file.
    "param pwr_scenario: Scenario to check.
    """
    ts_info(TsInfoCode.GENERIC, f"Checking scenario: {pwr_scenario}")
    if pwr_scenario not in ts_get_available_pwr_scenarios():
        ts_throw_error(TsErrCode.ERR_PWR_3, pwr_scenario, ts_get_available_pwr_scenarios())

def create_pwr_run_dir(pwr_scenario: str, seed: int):
    """
    Creates power run directory pwr/runs/<scenario>_<seed>_<runcode>_<date>.<time>
    :param pwr_scenario: Power scenario.
    :param seed: Simulation seed.
    """
    runs_dir = os.path.join(ts_get_root_rel_path(TsGlobals.TS_PWR_DIR), "runs")
    os.makedirs(runs_dir, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d.%H%M")
    run_dir_name = "{}_{}_{}_{}".format(pwr_scenario, seed, TsGlobals.TS_RUNCODE, now)
    TsGlobals.TS_PWR_RUN_DIR = os.path.join(runs_dir, run_dir_name)
    os.makedirs(TsGlobals.TS_PWR_RUN_DIR, exist_ok=True)
    os.makedirs(os.path.join(TsGlobals.TS_PWR_RUN_DIR, "tmp"), exist_ok=True)

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
            ts_script_bug(f"Invalid key \'{key}\' to get in list {lst}")

    ts_debug(f"No such item with \'{key}\' : \'{val}\' found in provided list")
    return []

def get_netlist_file() -> str:
    #TODO: This will be switched once pnr export directory structure and naming is solved
    #return os.path.join(TsGlobals.TS_RUNCODE_DIR, RUNCODE_RESULTS_DIR, f"{RUNCODE_FILE_PREFIX}.v")
    return get_netlist_from_slf("pnr_export/slf_netlist.yml")

def get_parasitic_file(mode: dict) -> str:
    return os.path.join(TsGlobals.TS_RUNCODE_DIR, RUNCODE_RESULTS_DIR,
                "{}.{}.spef".format(RUNCODE_FILE_PREFIX, CORNER_DICT[mode["corner"]]))

def get_vcd_file(scenario: dict, seed):
    ts_set_cfg("target", scenario["simulation_target"])
    sim_test = {"name": scenario["test_name"], "seed": seed}
    return os.path.join(ts_get_test_dir("sim", sim_test), "inter.vcd")

def get_pdk_views_for_common_config() -> str:
    """
    Returns pdk views needed for power analysis.
    :return: Constant 'nldm_db'
    """
    return "nldm_db"

def build_run_sim_cmd(scenario: dict, seed: int, args, clear=0):
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

    #TODO: integrate --dump-vcd with time window
    # ts_sim_run_args += "--dump-vcd {} {}".format(pwr_scenario["from"], pwr_scenario["to"])

    ts_sim_run_args += " --dump-waves"

    if args.recompile:
        ts_sim_run_args += " --recompile"

    if args.clear_sim and clear == 0:
        ts_sim_run_args += " --clear"

    if args.clear_sim_logs and clear == 0:
        ts_sim_run_args += " --clear-logs"

    if args.license_wait:
        ts_sim_run_args += " --license-wait"
    
    ts_sim_run_args += " --seed {}".format(seed)

    #TODO: This is not ideal :( universal dumping of VCD file is still in progress
    # TMP
    if args.vcd_dump == "tb":
        ts_sim_run_args += " --add-elab-options \""
        ts_sim_run_args += "-pvalue+tassic_tb_top.vcd_dump_enable=1"
        ts_sim_run_args += " -pvalue+tassic_tb_top.vcd_dump_on={}".format(scenario["from"])
        ts_sim_run_args += " -pvalue+tassic_tb_top.vcd_dump_off={}".format(scenario["to"])
        ts_sim_run_args += "\""
    else:
        ts_sim_run_args += " --add-elab-options \""
        ts_sim_run_args += "+vcs+dumpvars+inter.vcd"
        ts_sim_run_args += " +vcs+dumpon+{}000".format(scenario["from"])
        ts_sim_run_args += " +vcs+dumpoff+{}000".format(scenario["to"])
        ts_sim_run_args += "\""

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

def build_prime_time_cmd():
    """
    Builds command to run power analysis
    :return: command tu run
    """
    pt_shell_cmd_args = "-f {}".format(TsGlobals.TS_PWR_RUN_FILE)
    log_file = os.path.join(TsGlobals.TS_PWR_RUN_DIR, "pt_shell.log")
    pt_shell_cmd_args += f" -output_log_file {log_file}"

    set_args = "set RUN_DIR {}".format(TsGlobals.TS_PWR_RUN_DIR)
    pt_shell_cmd_args += f" -x \"{set_args}\""

    return f"pt_shell {pt_shell_cmd_args}"

def generate_pre_pwr_hook(path: str, args):
    """
    Generates pre-PrimeTime hook.
    :param path: Path where to generate it.
    :args: args
    """
    prehook_file = open(path, 'w')

    lines = []

    lines.append("##############################################\n")
    lines.append("# PrimeTime Pre-Hook file\n")
    lines.append("# Generated automatically by ts-hw-scripts\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append("puts \"RM-Info: Running script [info script]\"\n")
    lines.append("\n")

    prehook_file.writelines(lines)
    prehook_file.close()

def generate_post_pwr_hook(path: str, args):
    """
    Generates post-PrimeTime hook.
    :param path: Path where to generate it.
    :args: args
    """
    posthook_file = open(path, 'w')

    lines = []

    lines.append("##############################################\n")
    lines.append("# Post PrimeTime Hook file\n")
    lines.append("# Generated automatically by ts-hw-scripts\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append("puts \"RM-Info: Running script [info script]\"\n")
    lines.append("\n")

    if not args.stay_in_pt_shell:
        lines.append("exit")
        lines.append("\n")

    posthook_file.writelines(lines)
    posthook_file.close()

def generate_common_setup(path: str, args):
    """
    Generates common setup.
    :param path: Path where to generate it.
    :param args: args
    """
    ts_info(TsInfoCode.GENERIC, "Generating common setup.")

    design_cfg_cmd = build_design_cfg_cmd(path)
    exec_cmd_in_dir(TsGlobals.TS_PWR_RUN_DIR, design_cfg_cmd, args.no_pwr_out, args.no_pwr_out)

def generate_specific_pwr_setup(path: str, args, scenario: list, seed):
    """
    Generates specific power setup.
    :param scenario: Power scenario.
    :param args: args
    :param seed: Simulation seed.
    :param path: Path where to generate it.
    """
    ts_info(TsInfoCode.GENERIC, "Generating power setup.")

    mode = find_list(TsGlobals.TS_DESIGN_CFG["design"]["modes"], "name", scenario["mode"])

    # Create and open the setup file
    setup_file = open(path, "w")

    lines = []

    lines.append("##############################################\n")
    lines.append("# PrimeTime Variables setup file\n")
    lines.append("# Generated automatically by ts-hw-scripts\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append("puts \"RM-Info: Running script [info script]\"\n")
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Report and Result Directories\n")
    lines.append("##############################################\n")
    lines.append("set REPORTS_DIR \"{}/reports\"\n".format(TsGlobals.TS_PWR_RUN_DIR))
    lines.append("set RESULTS_DIR \"{}/results\"\n".format(TsGlobals.TS_PWR_RUN_DIR))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Library and Design Setup\n")
    lines.append("##############################################\n")
    lines.append("set search_path     \". $TS_NLDM_DB_VIEW_DIRS $search_path\"\n")
    lines.append("set target_library  [dict get $TS_NLDM_DB_VIEWS {}]\n".format(scenario["mode"].upper()))
    lines.append("set link_path       \"* $target_library\"\n")
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Waves Dumping Setup\n")
    lines.append("##############################################\n")
    if args.dump_pwr_waves or args.gui == "verdi":
        if args.gui == "verdi":
            lines.append("set WAVEFORM_FORMAT fsdb\n")
        else:
            lines.append("set WAVEFORM_FORMAT {}\n".format(args.dump_pwr_waves))
    else:
        lines.append("set WAVEFORM_FORMAT none\n")
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Netlist Setup\n")
    lines.append("##############################################\n")
    lines.append("set NETLIST_FILES \"{}\"\n".format(get_netlist_file()))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Non-DMSA Power Analysis Setup Section\n")
    lines.append("##############################################\n")
    sim_run_path = get_vcd_file(scenario, seed)
    lines.append("set ACTIVITY_FILE \"{}\"\n".format(sim_run_path))
    lines.append("set STRIP_PATH \"{}\"\n".format(TsGlobals.TS_PWR_CFG["strip_path"]))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Back Annotation File Section\n")
    lines.append("##############################################\n")
    lines.append("set PARASITIC_FILE \"{}\"\n".format(get_parasitic_file(mode)))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# Constraint Section Setup\n")
    lines.append("##############################################\n")
    
    lines.append("set CONSTRAINT_FILE \"{}\"\n".format(mode["constraints"]))
    lines.append("\n")

    lines.append("##############################################\n")
    lines.append("# End\n")
    lines.append("##############################################\n")
    lines.append("\n")

    lines.append("puts \"RM-Info: Completed script [info script]\"\n")

    setup_file.writelines(lines)
    setup_file.close()

def check_pwr_args(args):
    """
    Checks if arguments make sense.
    :param args: args.
    """
    if not args.scenario:
        ts_throw_error(TsErrCode.ERR_PWR_6)

    if args.gui not in {"verdi", None}:
        ts_warning(TsWarnCode.GENERIC, f"GUI {args.gui} is not supported. GUI wont be launched.")

    if TsGlobals.TS_RUNCODE == None:
        if not hasattr(args, "runcode") or args.runcode == None:
            ts_throw_error(TsErrCode.ERR_PWR_7)
        else:
            TsGlobals.TS_RUNCODE = args.runcode
            TsGlobals.TS_RUNCODE_DIR = os.path.join(TsGlobals.TS_PNR_EXPORT_PATH, TsGlobals.TS_RUNCODE)

def check_runcode_dir(scenarios):
    ts_debug(f"Checking runcode directory {TsGlobals.TS_RUNCODE_DIR}")
    if not os.path.exists(TsGlobals.TS_RUNCODE_DIR):
        ts_throw_error(TsErrCode.GENERIC,
            f"Runcode directory {TsGlobals.TS_RUNCODE_DIR} does not exists!")
    netlist_file_path = get_netlist_file()
    ts_debug(f"Checking netlist {netlist_file_path}")
    if not os.path.exists(netlist_file_path):
        ts_throw_error(TsErrCode.GENERIC,
            f"Netlist {netlist_file_path} does not exists!")
    for s in scenarios:
        mode = find_list(TsGlobals.TS_DESIGN_CFG["design"]["modes"], "name", s["mode"])
        parasitic_file = get_parasitic_file(mode)
        ts_debug(f"Checking parasitic file {parasitic_file}")
        if not os.path.exists(parasitic_file):
            ts_throw_error(TsErrCode.GENERIC,
                "Parasitic file {} for scenario \'{}\' does not exists!".format(parasitic_file, s["name"]))

def check_vcd(scenario: dict, seed):
    vcd_file = get_vcd_file(scenario, seed)
    if not os.path.exists(vcd_file):
        ts_throw_error(TsErrCode.GENERIC,
            f"VCD file {vcd_file} does not exists!")

def check_primetime_run_script():
    if not os.path.exists(TsGlobals.TS_PWR_RUN_FILE):
        ts_throw_error(TsErrCode.GENERIC,
            f"PrimeTime run script {TsGlobals.TS_PWR_RUN_FILE} does not exists!")

def get_pwr_waves_path():
    """
    Gets path to power waves.
    """
    return os.path.join(TsGlobals.TS_PWR_RUN_DIR, "reports", "wave.fsdb")

def get_optional_key(dictionary: dict, key: str):
    """
    Gets value of item by key that is optional in dictionary.
    :return: Value of the item, if present, False otherwise.
    """
    if key in dictionary.keys():
        return dictionary[key]
    else:
        return False

def get_scenarios_to_run(scenarios_names: list) -> list:
    """
    Creates list of scenarios to be executed from 'scenario names' passed from command line.
    Uses unix like star completion.
    :param scenarios_names: List of scenario names to be queried, may contain wild-cards.
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
