# -*- coding: utf-8 -*-

####################################################################################################
# Common functions for Tropic Square simulation scripting system.
#
# TODO: License
####################################################################################################

import contextlib
import os
import shutil
import random
import re
import signal
import subprocess
from datetime import datetime

import junit_xml
import psutil
import yaml

from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import TsErrCode, ts_debug, ts_print, ts_script_bug, ts_throw_error


def concat_keys(in_lst: list, key: str, sep: str):
    """
    Concatenate key values from list of dictionaries
    """
    ret_val = ""
    # print(in_lst)
    for obj in in_lst:
        if key in obj:
            ret_val += obj[key]
        if not obj == in_lst[-1]:
            ret_val += sep
    return ret_val


def expand_vars(cfg):
    """
    Expand the environment variables in strings
    """
    if isinstance(cfg, dict):
        return {k: expand_vars(v) for k, v in cfg.items()}
    elif isinstance(cfg, list):
        return [expand_vars(e) for e in cfg]
    elif isinstance(cfg, str):
        expanded_cfg = os.path.expandvars(cfg)
        if expanded_cfg.isdecimal():
            expanded_cfg = int(expanded_cfg)
        return expanded_cfg
    return cfg


def __beautify_path(function):
    """
    Return a beautiful, normalized path
    Used as a decorator
    """

    def new_function(*args):
        return os.path.normpath(function(*map(expand_vars, args)))

    return new_function


@__beautify_path
def get_repo_root_path():
    """
    Returns HW repository root variable.
    """
    repo_root = os.getenv(TsGlobals.TS_REPO_ROOT)
    if not repo_root:
        ts_throw_error(
            TsErrCode.GENERIC,
            "${} is not defined! Run '{}' script.".format(
                TsGlobals.TS_REPO_ROOT, TsGlobals.TS_CONFIG_ENV_SCRIPT
            ),
        )
    return repo_root


def get_env_var_path(env_variable):
    """
    Returns content of enviromental variable that is used as a path container
    : param : Expected TsGlobals variable
    """
    env_var = os.getenv(env_variable)
    if not env_var:
        ts_throw_error(TsErrCode.GENERIC, f"{env_variable} is not defined!")

    return env_var


@__beautify_path
def ts_get_env_var_path(env_variable, *paths):
    """
    : param paths: Path to a file
    : param enviromental variable that is used as a path container
    : return: absolute path corresponding to following rules:
            1. If input path is absolute, treat it as it is (return itself)
            2. If input path is relative, treat is as relative to to enviromental variable which is parameter
    """
    return os.path.join(get_env_var_path(env_variable), *paths)


@__beautify_path
def ts_get_root_rel_path(*paths):
    """
    :param path: Path to a file
    :return: absolute path corresponding to following rules:
        1. If input path is absolute, treat it as it is (return itself)
        2. If input path is relative, treat it as relative to TS_REPO_ROOT variable
    """
    return os.path.join(get_repo_root_path(), *paths)


@__beautify_path
def ts_get_file_rel_path(file_path: str, path: str):
    """
    :param file_path: Path to source file (must be absolute!) from which we want to derive
           relative path.
    :param path: Path to a file
    :return: absolute path corresponding to following rules:
        1. If input 'path' is absolute, treat it as it is (return itself)
        2. If input 'path' is relative, treat it as relative to 'file_path'.
    """
    ret_path = os.path.join(os.path.dirname(file_path), path)
    if not os.path.isabs(ret_path):
        ts_script_bug(f"Root file path '{file_path}' shall be passed as absolute!")
    return ret_path


@__beautify_path
def ts_get_curr_dir_rel_path(*paths):
    """
    :param path: Path to a file
    :return: absolute path corresponding to following rules:
        1. If input 'path' is absolute, treat it as it is (return itself)
        2. If input 'path' is relative, treat it as relative to current directory.
    """
    return os.path.join(os.getcwd(), *paths)


def load_yaml_file(yaml_file: str) -> dict:
    """
    Utility to load a yaml file
    """
    if not yaml_file.endswith(".yml"):
        ts_throw_error(
            TsErrCode.GENERIC,
            f"File name '{yaml_file}' shall end with '.yml' suffix (YAML file extension).",
        )

    try:
        with open(yaml_file) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"{yaml_file} config file was not found. Make sure it exists!",
        )
    except:
        ts_throw_error(
            TsErrCode.GENERIC,
            f"Failed to load {yaml_file} config file probably due "
            "to incorrect YAML syntax.",
        )


def check_target(design_target: str):
    """
    Checks if simulation target is defined in simulation configuration. Throws exception if not.
    :param design_target Target name to be checked
    """
    ts_debug(f"Checking target: {design_target}")
    if design_target not in ts_get_cfg("targets"):
        ts_throw_error(
            TsErrCode.ERR_CFG_8, design_target, list(ts_get_cfg("targets").keys())
        )


def create_sim_sub_dir(name: str):
    """
    Create log file directory in "sim" folder.
    :param name: Name of the sub-directory within TS_REPO_ROOT/sim directory to be created.
    """
    os.makedirs(ts_get_root_rel_path(name), exist_ok=True)


def ts_get_cfg(cfg_key=None):
    """
    :param cfg_key: if set returns value from root dictionary of global configuration. If not,
    returns root dictionary itself. Throws exception if key is not present in global configuration.
    """
    if cfg_key is None:
        return TsGlobals.TS_SIM_CFG

    try:
        return TsGlobals.TS_SIM_CFG[cfg_key]
    except KeyError:
        ts_debug(TsGlobals.TS_SIM_CFG)
        ts_script_bug(f"Invalid key '{cfg_key}' to get in global configuration")


def ts_set_cfg(cfg_key: str, cfg_val):
    """
    Sets value in root dictionary of global configuration.
    :param cfg_key: Configuration key to be set
    :param cfg_val: Configuration value to be set for given key
    """
    TsGlobals.TS_SIM_CFG[cfg_key] = cfg_val


def ts_is_uvm_enabled():
    """
    Checks if UVM is enabled (globally, or per-target)
    """
    return (
        ts_get_cfg("enable_uvm")
        or ts_get_cfg("targets")[ts_get_cfg("target")]["enable_uvm"]
    )


def create_log_file_name(log_file_type, test=None):
    """
    Creates log file name specific for a given test.
    :param log_file_type: sim/elab for type of log
    :param test: test
    """

    if ts_get_cfg("timestamp_log_file"):
        timestamp = datetime.now().strftime("_%Y_%m_%d_%H_%M_%S_%f")
    else:
        timestamp = ""

    if log_file_type == "sim":
        directory = TsGlobals.TS_SIM_LOG_DIR_PATH
        test_info = "_{}_{}".format(test["name"], test["seed"])
    elif log_file_type == "elab":
        directory = TsGlobals.TS_ELAB_LOG_DIR_PATH
        test_info = "_" + test["name"]
    elif log_file_type == "compile":
        directory = TsGlobals.TS_COMP_LOG_DIR_PATH
        test_info = ""
    else:
        raise NotImplementedError(f"Unsupported log file type '{log_file_type}'")

    return ts_get_root_rel_path(
        directory,
        "{}_{}{}{}.log".format(
            log_file_type, ts_get_cfg("target"), test_info, timestamp
        ),
    )


def get_regression_dest_dir_name():
    return ts_get_root_rel_path(
        TsGlobals.TS_SIM_DIR,
        "regression_{}".format(datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")),
    )


def ts_is_at_least_verbose():
    """
    :return: True if verbosity is set to "verbose" or "very verbose", False otherwise
    """
    return ts_get_cfg("verbose") >= 1


def ts_is_very_verbose():
    """
    :return: True if verbosity is set to "very verbose", False otherwise.
    """
    return ts_get_cfg("verbose") >= 2


def ts_generate_seed():
    """
    Generates seed for simulation.
    """
    # Override seed if defined
    if ts_get_cfg().get("seed") is not None:
        return ts_get_cfg("seed")
    else:
        return random.randint(0, 1000000)


def ts_get_test_dir(dir_type, test):
    """
    :param test: Test object (dictionary loaded from test list file)
    :return: Path of directory
    """
    if dir_type == "sim":
        return os.path.join(
            ts_get_cfg("build_dir"),
            "{}_{}_{}_{}".format(
                dir_type, ts_get_cfg("target"), test["name"], test["seed"]
            ),
        )
    elif dir_type == "elab":
        dir_path_base = os.path.join(
            ts_get_cfg("build_dir"),
            "{}_{}_{}_{{:0=3d}}".format(dir_type, ts_get_cfg("target"), test["name"]),
        )
        for i in range(1000):
            dir_path = dir_path_base.format(i)
            if not os.path.isdir(dir_path):
                return dir_path
        else:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"Reached the limit of '{i+1}' elaboration directories!",
            )
    else:
        ts_script_bug(f"Directory type '{dir_type}' not supported!")


# Warning: make sure you know what you are doing!
__FORBIDDEN_LINES = {
    "/tools/synopsys/vcs/R-2020.12-SP2-0/bin/vlogan: line 137: /tools/synopsys/vcs/R-2020.12-SP2-0/linux/bin/vcsparse: No such file or directory\n"
}


def exec_cmd_in_dir(
    directory: str, command: str, no_std_out: bool = False, no_std_err: bool = False
) -> int:
    """
    Executes a command in a directory.
    :param directory: Directory in which command shall be executed
    :param command: Command to execute.
    """

    def __raise_timeout(*args):
        raise TimeoutError

    # Redirect both standard flows stdout and stderr to the same one
    # so we can process the lines in order
    if (no_std_out, no_std_err) == (False, False):
        opts = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT}
        output = "stdout"
    elif (no_std_out, no_std_err) == (True, False):
        opts = {"stdout": subprocess.DEVNULL, "stderr": subprocess.PIPE}
        output = "stderr"
    elif (no_std_out, no_std_err) == (False, True):
        opts = {"stdout": subprocess.PIPE, "stderr": subprocess.DEVNULL}
        output = "stdout"
    else:  # (no_std_out, no_std_err) == (True, True):
        opts = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        output = ""

    ts_debug(f"Executing command in directory '{directory}'")

    # Launch the command
    p = subprocess.Popen(
        command, shell=True, encoding="latin-1", cwd=directory, env=os.environ, **opts
    )

    with contextlib.suppress(AttributeError):
        signal.signal(signal.SIGALRM, __raise_timeout)
        no_color = ts_get_cfg("no_color")
        color_regex = re.compile("\x1b\[[0-9]{1,2}m")
        # Manage lines while process is running
        while p.poll() is None:
            # Read a new line
            try:
                # Define a timeout for reading the line
                signal.alarm(2)
                line = getattr(p, output).readline()
            except TimeoutError:
                continue
            finally:
                signal.alarm(0)
            # Filter
            if line in __FORBIDDEN_LINES:
                continue
            # Remove color of line if need be
            if no_color:
                line = color_regex.sub("", line)
            # Display
            ts_print(line, end="")
    signal.alarm(0)
    return p.wait()


def generate_junit_test_object(
    test_result: dict, log_file_path: str, export_logs=False
):
    """
    Generates JUnit report which can be parsed by Gitlab
    :param export_logs: Is set, simulation/elaboration log files will be exported.
    :param test_result: Results object of single test as parsed by ts_sim_check.py
    :param log_file_path: Log file path
    """
    if export_logs:
        with open(log_file_path) as fd:
            sim_logs = fd.read()
    else:
        sim_logs = "Log file not exported! Run with '--junit-exp-logs' "

    test = junit_xml.TestCase(
        test_result["log_file_name"],
        elapsed_sec=test_result["run_time"],
        stdout=sim_logs,
    )

    for err in test_result["errors"]:
        test.add_error_info(err)

    if ts_get_cfg("check_severity") == "warning":
        for warn in test_result["warnings"]:
            test.add_error_info(warn)

    return test


def gracefully_quit(sig, frame):
    """
    Exit the current process in a clean way
    """
    children = psutil.Process().children(recursive=True)
    for child in reversed(children):
        # the soft way
        ts_debug(f"Terminating process {child}")
        child.terminate()

    gone, alive = psutil.wait_procs(children, timeout=2)

    for child in alive:
        # the hard way
        ts_debug(f"Killing process {child}")
        child.kill()

    ts_throw_error(TsErrCode.ERR_CMP_5, signal.Signals(sig).name)


def propagate_to_parent(sig, frame):
    """
    Send signal to parent process
    """
    parent = psutil.Process().parent()
    ts_debug(f"Sending signal {signal.Signals(sig).name} to parent {parent}")
    parent.send_signal(sig)


def init_signals_handler():
    """
    Initialize external signals handling
    """
    signal.signal(signal.SIGINT, gracefully_quit)
    signal.signal(signal.SIGTERM, gracefully_quit)
    signal.signal(signal.SIGUSR1, propagate_to_parent)


def get_pdk_obj(obj_type: str, target_obj_name: str, target_obj_version: str) -> dict:
    """ """
    assert obj_type == "std_cells" or obj_type == "ips"

    pdk_name = TsGlobals.TS_DESIGN_CFG["design"]["pdk"]
    target_pdk = None

    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk_name == pdk["name"]:
            target_pdk = pdk

    assert target_pdk is not None

    for obj in target_pdk[obj_type]:
        # print(obj)
        if obj["name"] == target_obj_name and obj["version"] == target_obj_version:
            return obj

    # We should never get here since loading of design config file guarantees that
    # std_cells and IPs referred to are consistent
    assert False


def get_pdk_corners() -> dict:
    """ """
    pdk_name = TsGlobals.TS_DESIGN_CFG["design"]["pdk"]

    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk_name == pdk["name"]:
            target_pdk = pdk

    assert target_pdk is not None

    return target_pdk["corners"]

    # We should never get here since loading of design config file guarantees that
    # std_cells and IPs referred to are consistent
    assert False


def view_has_corner(pdk_view: str):
    """
    Returns True if given view shall have per-corner value, False otherwise
    :param pdk_view: Name of the view
    """
    if (
        pdk_view == "nldm_lib"
        or pdk_view == "nldm_db"
        or pdk_view == "ccs_lib"
        or pdk_view == "ccs_db"
    ):
        return True
    return False


def is_used_corner(corner: str):
    """ """
    for mode in TsGlobals.TS_DESIGN_CFG["modes"]:
        if mode["corner"] == corner:
            return True
    return False


def get_used_corners():
    """ """
    raw_list = []
    filtered_list = []
    for mode in TsGlobals.TS_DESIGN_CFG["modes"]:
        raw_list.append(mode["corner"])
    [filtered_list.append(x) for x in raw_list if x not in filtered_list]
    return filtered_list


def get_mode_for_corner(corner: str):
    """ """
    for mode in TsGlobals.TS_DESIGN_CFG["modes"]:
        if mode["corner"] == corner:
            return mode
    ts_script_bug(
        "Mode not found for corner -> Was the Design config file checked properly during parsing?"
    )


def ts_get_design_top():
    """ """
    return (
        ts_get_cfg()["targets"][ts_get_cfg()["target"]]["top_entity"]
        .split(".")[-1]
        .upper()
    )


def ts_set_env_var(var: str, val: str):
    os.environ[var] = val
    if (not var in os.environ) or (os.environ[var] != val):
        ts_throw_error(TsErrCode.GENERIC, f"Failed to set environment variable {var}!")


def ts_unset_env_var(var: str):
    os.environ.pop(var, None)
    if var in os.environ:
        ts_throw_error(
            TsErrCode.GENERIC, f"Failed to unset environment variable {var}!"
        )

def ts_rmdir(dir: str):
    for dir_prefix in TsGlobals.TS_DIR_DONT_TOUCH:
        if dir.startswith(dir_prefix):
            ts_throw_error(
                TsErrCode.GENERIC, f"Failed to remove directory {dir}! {dir_prefix} is in TS_DIR_DONT_TOUCH list."
            )
    shutil.rmtree(dir, ignore_errors=True)
    