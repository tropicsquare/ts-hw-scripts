# -*- coding: utf-8 -*-

####################################################################################################
# Common functions for Tropic Square simulation scripting system.
#
# TODO: License
####################################################################################################

import io
import os
from re import sub
import sys
from datetime import datetime
import time
import random
import yaml
import junit_xml
import signal
import psutil
import contextlib
import subprocess
from .ts_hw_logging import *
from .ts_hw_global_vars import *


def __beautify_path(function):
    """
    Return a beautiful, normalized path
    Used as a decorator
    """
    def new_function(*args, **kwargs):
        return os.path.normpath(function(*args, **kwargs))
    return new_function


@__beautify_path
def get_repo_root_path():
    """
    Returns HW repository root variable.
    """
    repo_root = os.getenv(TsGlobals.TS_REPO_ROOT)
    if not repo_root:
        ts_throw_error(TsErrCode.ERR_ENV_0)
    return repo_root


@__beautify_path
def ts_get_root_rel_path(path: str):
    """
    :param path: Path to a file
    :return: absolute path corresponding to following rules:
        1. If input path is absolute, treat it as it is (return itself)
        2. If input path is relative, treat it as relative to TS_REPO_ROOT variable
    """
    if os.path.isabs(path):
        return path
    return os.path.join(get_repo_root_path(), path)


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
    if not os.path.isabs(file_path):
        ts_script_bug("Root file path '{}' shall be passed as absolute!".format(file_path))
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.dirname(file_path), path)


@__beautify_path
def ts_get_curr_dir_rel_path(path: str):
    """
    :param path: Path to a file
    :return: absolute path corresponding to following rules:
        1. If input 'path' is absolute, treat it as it is (return itself)
        2. If input 'path' is relative, treat it as relative to current directory.
    """
    if os.path.isabs(path):
        return path
    return os.path.join(os.getcwd(), path)


def check_list_file_present(list_file_path: str):
    """
    Checks if source list file is present. Throws exception if not.
    :param list_file_path: Source list file path
    """
    if not os.path.isfile(list_file_path):
        ts_throw_error(TsErrCode.ERR_SLF_0, list_file_path)
    if not str(list_file_path).endswith(".yml"):
        ts_throw_error(TsErrCode.ERR_SLF_7, list_file_path)


def check_target(design_target: str):
    """
    Checks if simulation target is defined in simulation configuration. Throws exception if not.
    :param design_target Target name to be checked
    """
    ts_debug("Checking target: {}".format(design_target))
    if design_target not in TsGlobals.TS_SIM_CFG["targets"]:
        ts_throw_error(TsErrCode.ERR_CFG_8, design_target, 
                                            list(TsGlobals.TS_SIM_CFG["targets"].keys()))


def check_valid_test_name(test_name: str, path: str):
    """
    Checks if name does not contain special characters. Throws exception if yes.
    Test names shall not contain special characters to allow specifying wild-card names.
    :param test_name: Name of the test
    :param path: Path to a file in which test name is being checked
    """
    common_characters = set(test_name) & set("[@!#$%^&*()<>?/\|}{~:]")
    if common_characters:
        ts_throw_error(TsErrCode.ERR_SLF_12, common_characters, test_name, path)


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
        ts_debug(str(TsGlobals.TS_SIM_CFG))
        ts_script_bug("Invalid key '{}' to get in global configuration".format(cfg_key))


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
    return bool(ts_get_cfg("enable_uvm") or ts_get_cfg("targets")[ts_get_cfg("target")]["enable_uvm"])


def create_log_file_name(seed, current_test_name, log_file_type):
    """
    Creates log file name specific for a given test.
    :param seed: Current test seed.
    :param current_test_name: Name of the test
    :param log_file_type: sim/elab for type of log
    """

    if log_file_type == "sim":
        directory = TsGlobals.TS_SIM_LOG_DIR_PATH
    else:
        directory = TsGlobals.TS_ELAB_LOG_DIR_PATH
        
    if ts_get_cfg("timestamp_log_file"):
        timestamp_str = "_{}".format(datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
    else:
        timestamp_str = ""

    return os.path.join(get_repo_root_path(), directory, "{}_{}_{}_{}{}.log".format(
                        log_file_type, ts_get_cfg("target"), current_test_name, seed, timestamp_str))


@__beautify_path
def get_regression_dest_dir_name():
    return os.path.join(get_repo_root_path(), TsGlobals.TS_SIM_DIR,
            "regression_{}".format(datetime.now().strftime("%Y_%m_%d_%H_%M_%S")))


def ts_is_at_least_verbose():
    """
    :return: True if verbosity is set to "verbose" or "very verbose", False otherwise
    """
    return bool(ts_get_cfg("verbose") or ts_get_cfg("very_verbose"))


def ts_is_very_verbose():
    """
    :return: True if verbosity is set to "very verbose", False otherwise.
    """
    return bool(ts_get_cfg("very_verbose"))


def ts_generate_seed():
    """
    Generates seed for simulation.
    """
    # Over-rider seed if it is defined!
    if ts_get_cfg().get("seed") is not None:
        return ts_get_cfg("seed")
    else:
        return random.randint(0, 1000000)


@__beautify_path
def ts_get_test_binary_dir(test):
    """
    :param test: Test object (dictionary loaded from test list file)
    :return: Path of test specific directory in which elaboration will run an simulation binary
             will be created!
    """
    return ts_get_root_rel_path(os.path.join(TsGlobals.TS_SIM_BUILD_PATH, "{}_{}_{}".format(
        ts_get_cfg("target"), test["name"], test["seed"])))


# Warning: make sure you know what you are doing!
__FORBIDDEN_LINES = {
'/tools/synopsys/vcs/R-2020.12-SP2-0/bin/vlogan: line 137: /tools/synopsys/vcs/R-2020.12-SP2-0/linux/bin/vcsparse: No such file or directory\n'
}


def exec_cmd_in_dir(directory: str, command: str, no_std_out: bool = False, no_std_err: bool = False) -> int:
    """
    Executes a command with "chdir" to another directory.
    :param directory: Directory in which command shall be executed
    :param command: Command to execute.
    """
    @contextlib.contextmanager
    def _timeout(duration):
        """
        This context manager exits after 'duration' seconds
        """
        def __raise_timeout(*args):
            raise TimeoutError

        signal.signal(signal.SIGALRM, __raise_timeout)
        signal.alarm(duration)
        try:
            yield
        except TimeoutError:
            pass
        finally:
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            signal.alarm(0)


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
    else: # (no_std_out, no_std_err) == (True, True):
        opts = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        output = ""

    ts_debug(f"Changing directory before command execution to: {directory}")
    old_dir = os.getcwd()
    os.chdir(directory)

    # Launch the command
    try:
        p = subprocess.Popen(command, shell=True, encoding="latin-1", env=os.environ, **opts)
        while True:
            line = ''
            # Read a new line, filter and display it
            with _timeout(1):
                line = getattr(p, output).readline()
            if line in __FORBIDDEN_LINES:
                continue
            print(line, end='')
            # Check if process is still running
            if p.poll() is not None:
                break
        return p.wait()
    except AttributeError:
        return p.wait()
    finally:
        os.chdir(old_dir)


def generate_junit_test_object(test_result: dict, log_file_path: str, export_logs=False):
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

    test = junit_xml.TestCase(test_result["log_file_name"], elapsed_sec=test_result["run_time"],
                              stdout=sim_logs)

    for err in test_result["errors"]:
        test.add_error_info(err)

    for ign_err in test_result["ignored_errors"]:
        test.add_skipped_info(ign_err)

    return test


def kill_children_processes(process: psutil.Process):
    """
    Recursively kills all the children processes of a process
    """
    for child_process in process.children():
        with contextlib.suppress(psutil.NoSuchProcess):
            kill_children_processes(child_process)
    # do not kill current process
    if process == psutil.Process():
        return
    try:
        # the soft way
        process.terminate()
        process.wait(timeout=1)
    except psutil.TimeoutExpired:
        # the hard way
        process.kill()


def gracefully_quit(sig, frame):
    """
    Exit the current process in a clean way
    """
    kill_children_processes(psutil.Process())
    ts_throw_error(TsErrCode.ERR_CMP_5, signal.Signals(sig).name)


def init_signals_handler():
    """
    Initialize external signals handling
    """
    signal.signal(signal.SIGINT, gracefully_quit)
    signal.signal(signal.SIGTERM, gracefully_quit)

