# -*- coding: utf-8 -*-

####################################################################################################
# Routines for checking simulation results
#
# TODO: License
####################################################################################################
import os
import re
import copy

from .ts_hw_logging import *
from .ts_hw_common import *
from .ts_hw_global_vars import *
from .ts_grammar import *


__RESULT_FORMAT = "{:80}{:14}{:10}{:12}{:10}{:12}{:15}"
# small trick so the separator has always the same length as the lines of the result summary
__SEPARATOR = '*' * len(__RESULT_FORMAT.format(*(" " for i in range(len(__RESULT_FORMAT)))))

__IGNORE_ERR = False
__IGNORE_WARN = False
__UVM_REPORT_SUMMARY = False

__ERR_REGEXES = []
__WARN_REGEXES = []

__EMPTY_TEST_RESULTS = {
    "result": True,
    "warnings": [],
    "errors": [],
    "ignored_errors": [],
    "ignored_warnings": [],
    "log_file_name": None,
    "sim_exit_code": 0,
    "run_time": None
}


def __match_line_to_patterns(line: str, patterns: list):
    """
    Checks if line matches to a list of patterns.
    :param line: Input string to be matched
    :param patterns: List of compiled regular expression patterns to be searched.
    :return: None if it does not match, line itself if yes
    """
    for pattern in patterns:
        match = pattern.search(line)
        if match:
            if not ts_get_cfg("no_color"):
                return line.replace(match.group(), TsColors.RED + match.group() + TsColors.END)
            return line


def __check_ignore(line: str):
    """
    Checks if errors/warnings should not start/stop being ignored!
    :param line: Current line being parsed
    """
    global __IGNORE_ERR
    global __IGNORE_WARN

    if "error_ignore_start" in ts_get_cfg():
        if not __IGNORE_ERR and re.search(ts_get_cfg("error_ignore_start"), line):
            ts_debug(f"Starting error patterns ignore from line: '{line.strip()}'")
            __IGNORE_ERR = True
        elif __IGNORE_ERR and re.search(ts_get_cfg("error_ignore_stop"), line):
            ts_debug(f"Stopping error patterns ignore from line: '{line.strip()}'")
            __IGNORE_ERR = False

    if "warning_ignore_start" in ts_get_cfg():
        if not __IGNORE_WARN and re.search(ts_get_cfg("warning_ignore_start"), line):
            ts_debug(f"Starting warning patterns ignore from line: '{line.strip()}'")
            __IGNORE_WARN = True
        elif __IGNORE_WARN and re.search(ts_get_cfg("warning_ignore_stop"), line):
            ts_debug(f"Stopping warning patterns ignore from line: '{line.strip()}'")
            __IGNORE_WARN = False


def __check_ignore_uvm(line: str):
    """
    Checks if UVM report summary is being printed, set "__UVM_REPORT_SUMMARY" if yes.

    """
    global __UVM_REPORT_SUMMARY
    
    if re.search(BUILT_IN_UVM_IGNORE_START_PATTERN, line):
        ts_debug(f"Starting UVM ignore on line: '{line.strip()}'")
        __UVM_REPORT_SUMMARY = True
    
    if re.search(BUILT_IN_UVM_IGNORE_STOP_PATTERN, line):
        ts_debug(f"Stopping UVM ignore on line: '{line.strip()}'")
        __UVM_REPORT_SUMMARY = False


def __read_log_trailer(lines) -> list:
    """
    Reads simulation/elaboration log trailer written by ts_sim_run
    :param lines: Read lines from the file
    """
    ts_debug("Check that sim exit code is appended!")
    if len(lines) < 2 or re.match(r"TS_(?:ELAB|SIM)_RUN_EXIT_CODE: [0-9]+\n", lines[-2]) is None:
        exit_code, run_time = -1, .0
    else:
        exit_code, run_time = int(lines[-2].split()[1]), float(lines[-1].split()[1])
    return exit_code, run_time


def __get_after_line(lines: list, line_num: int, num_lines_after: int) -> list:
    """
    :param lines: List of log file lines
    :param line_num: Number of line to start from
    :param num_lines_after: Number of after lines to return
    :return: number of lines after certain line number
    """
    return lines[line_num + 1 : line_num + 1 + num_lines_after]


def __prepare_regexes():
    """
    Precompiles regular expressions for Warning, Error patterns
    """
    global __ERR_REGEXES
    global __WARN_REGEXES

    __ERR_REGEXES = []
    __WARN_REGEXES = []

    kwds = (("error_patterns", __ERR_REGEXES) , ("warning_patterns", __WARN_REGEXES))

    for kwd, regexes in kwds:
        pats = ts_get_cfg(kwd)
        pattern_list = [*pats.get("common", []), *pats.get(ts_get_cfg("simulator"), [])]

        for pat in pattern_list:
            regexes.append(re.compile(pat))


def check_single_test(sim_log_file_path: str):
    """
    Checks result of a single test.
    :param sim_log_file_path: Simulation log file (TS_REPO_ROOT relative path)
    :return: Dictionary with following keys:
        'result' - True - Test passed, False - Test failed
        'warnings' - List of strings classified as warnings
        'errors' - List of strings classified as errors
    """
    global __IGNORE_ERR
    global __IGNORE_WARN
    global __UVM_REPORT_SUMMARY

    global __ERR_REGEXES
    global __WARN_REGEXES

    post_sim_msg_found = False
    uvm_report_summary_found = False

    # Expect test to 'pass' (return empty list)
    test_results = copy.deepcopy(__EMPTY_TEST_RESULTS)

    if not os.path.isabs(sim_log_file_path):
        ts_script_bug("'check_single_test' shall be called with absolute path!")

    if not os.path.exists(sim_log_file_path):
        ts_throw_error(TsErrCode.ERR_SIM_1, sim_log_file_path)

    test_results["log_file_name"] = os.path.basename(os.path.normpath(sim_log_file_path))

    with open(sim_log_file_path, encoding="latin-1") as sim_log_file:
        lines = sim_log_file.readlines()

    # Read additional information about the simulation from the log file
    test_results["sim_exit_code"], test_results["run_time"] = __read_log_trailer(lines)

    if test_results["sim_exit_code"] != 0:
        test_results["result"] = False
        test_results["errors"].append({"line_number": 0,
                                        "line": "Simulation failed with exit code: {}".format(
                                                    test_results["sim_exit_code"])})
        if test_results["sim_exit_code"] == -1:
            test_results["errors"].append({"line_number": 0,
                                            "line": "Exit code -1 means that simulation exit code "
                                                    "was not written to log file properly!"})

    # Prepares regular expressions for faster performance
    __prepare_regexes()

    # Append line numbers
    numbered_lines = [{"line_number": line_number, "line": line} for line_number, line in enumerate(lines)]

    # Check errors and warnings for each line, appends match
    for log_line in numbered_lines:

        if ts_is_uvm_enabled():
            __check_ignore_uvm(log_line["line"])

            # Skip further processing of this line. No need to include UVM_ERROR into list of ignored errors.
            if __UVM_REPORT_SUMMARY:
                uvm_report_summary_found = True
                continue

        # Check if line matches "post_sim_msg" if it exists
        if not post_sim_msg_found and ts_get_cfg("post_sim_msg"):
            if re.search(ts_get_cfg("post_sim_msg"), log_line["line"]):
                post_sim_msg_found = True
                continue

        __check_ignore(log_line["line"])

        err = __match_line_to_patterns(log_line["line"], __ERR_REGEXES)
        if err:
            log_line["line"] = err
            log_line["after_lines"] = __get_after_line(numbered_lines, log_line["line_number"], 1)
            if __IGNORE_ERR:
                test_results["ignored_errors"].append(log_line)
            else:
                test_results["errors"].append(log_line)
                test_results["result"] = False
            continue

        warn = __match_line_to_patterns(log_line["line"], __WARN_REGEXES)
        if warn:
            log_line["line"] = warn
            log_line["after_lines"] = __get_after_line(numbered_lines, log_line["line_number"], 1)
            if __IGNORE_WARN:
                test_results["ignored_warnings"].append(log_line)
            else:
                test_results["warnings"].append(log_line)
            # Warnings cause test to fail only when error severity is warning!
            if ts_get_cfg("check_severity") == "warning":
                test_results["result"] = False

    # Check that when we finished parsing the log file, both ignore errors and ignore warnings are
    # not set! Fail otherwise!
    if __IGNORE_ERR or __IGNORE_WARN:
        test_results["result"] = False
        test_results["errors"].append({
                    "line": "Simulation ended with ignoring errors and/or warnings! This is forbidden!",
                    "line_number": 0})

    ## Check that if post_sim_msg is defined, it has been found
    if ts_get_cfg("post_sim_msg") and not post_sim_msg_found:
        test_results["result"] = False
        test_results["errors"].append({
                    "line": "Simulation ended without printing '{}' into log. '{}' is value " \
                           "of 'post_sim_msg' keyword. If you set this keyword, testbench must print " \
                           "this value to simulation log file, otherwise test will be marked " \
                           "as failed!".format(ts_get_cfg("post_sim_msg"), ts_get_cfg("post_sim_msg")),
                    "line_number": 0})

    # Make sure that UVM report summary has been found in a UVM test
    # Ignore on elaboration logs!
    if ts_is_uvm_enabled() and not uvm_report_summary_found and \
        not os.path.basename(sim_log_file_path).startswith("elab"):
        test_results["result"] = False
        test_results["errors"].append({
                    "line": "UVM simulation ended without UVM report summary!",
                    "line_number": 0})

    return test_results


def print_test_result(test_result: list):
    """
    Prints result of a single test.
    :param test_result: Results objet of single test
    """
    undefined_keys = set(__EMPTY_TEST_RESULTS.keys()) - set(test_result.keys())
    if undefined_keys:
        ts_script_bug(f"{undefined_keys} key(s) shall be defined in test results.")

    __to_text = lambda r: [[f"{TsColors.RED}FAIL{TsColors.END}", "FAIL"],
                            [f"{TsColors.GREEN}PASS{TsColors.END}", "PASS"]][r][ts_get_cfg("no_color")]

    ts_print(__RESULT_FORMAT.format(*map(str, (
                                    test_result["log_file_name"],
                                    "{:.1f}".format(test_result["run_time"]),
                                    len(test_result["errors"]),
                                    len(test_result["warnings"]),
                                    len(test_result["ignored_errors"]),
                                    len(test_result["ignored_warnings"]),
                                    __to_text(test_result["result"])))))

    if ts_is_at_least_verbose():
        for item in ("errors", "warnings", "ignored_errors", "ignored_warnings"):
            ts_print(f"List of {item.replace('_', ' ')}:", color=TsColors.PURPLE)
            for entry in test_result[item]:
                ts_print(f"Line {entry['line_number']}: " + entry["line"].rstrip(),
                            *map(lambda x: "\t" + x["line"].rstrip(),
                                entry.get("after_lines", [])),
                            sep="\n")


def print_test_result_header():
    """
    Prints test results header.
    """
    ts_print(__SEPARATOR,
            __RESULT_FORMAT.format("Test log file", "Run-time(s)", "Errors", "Warnings",
                                      "Ignored", "Ignored", "Result"),
            __RESULT_FORMAT.format("", "", "", "", "Errors", "Warnings", ""),
            __SEPARATOR,
            sep="\n")


def print_test_summary(total_run_time, total_err, total_warn, ign_err, ign_warn, failed_cnt,
                       total_cnt):
    """
    Prints test summary with total number of errors/warnings, passed/failed tests, etc.
    """
    ts_print(__SEPARATOR,
            __RESULT_FORMAT.format(*map(str, (
                                    "Summary",
                                    "{:.1f}".format(total_run_time),
                                    total_err,
                                    total_warn,
                                    ign_err,
                                    ign_warn,
                                    "PASS: {}/{}".format(total_cnt - failed_cnt, total_cnt)))),
            __SEPARATOR,
            sep="\n")

