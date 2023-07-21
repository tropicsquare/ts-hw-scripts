# -*- coding: utf-8 -*-

####################################################################################################
# Routines for checking simulation results
#
# TODO: License
####################################################################################################
import os
import re

from .ts_grammar import (
    BUILT_IN_UVM_IGNORE_START_PATTERN,
    BUILT_IN_UVM_IGNORE_STOP_PATTERN,
)
from .ts_hw_common import ts_get_cfg, ts_is_at_least_verbose, ts_is_uvm_enabled
from .ts_hw_logging import (
    TsColors,
    TsErrCode,
    TsInfoCode,
    ts_debug,
    ts_info,
    ts_print,
    ts_throw_error,
)


class TSLogChecker:
    """
    Checks logs as quickly as possible
    """

    RESULT_FORMAT = "{:95}{:14}{:10}{:12}{:10}{:12}{:15}"
    # small trick so the separator has always the same length as the lines of the result summary
    SEPARATOR = "*" * len(
        RESULT_FORMAT.format(*(" " for i in range(len(RESULT_FORMAT))))
    )

    LINES_AFTER = 1

    LOG_TRAILER_REGEX = re.compile(r"TS_(?:ELAB|SIM)_RUN_EXIT_CODE: [0-9]+\n")
    UVM_IGNORE_START_PATTERN_REGEX = re.compile(BUILT_IN_UVM_IGNORE_START_PATTERN)
    UVM_IGNORE_STOP_PATTERN_REGEX = re.compile(BUILT_IN_UVM_IGNORE_STOP_PATTERN)

    def __init__(self):
        # Initialize instance variables
        global_config = ts_get_cfg()
        self.global_config = global_config

        self.errors_regex, self.warnings_regex = self._prepare_regexes()
        self.uvm_is_enabled = ts_is_uvm_enabled()

        if "post_sim_msg" in global_config:
            self.post_sim_msg_regex = re.compile(global_config["post_sim_msg"])
        else:
            self.post_sim_msg_regex = None

        if "error_ignore_start" in global_config:
            self.error_ignore_start_regex = re.compile(
                global_config["error_ignore_start"]
            )
            self.error_ignore_stop_regex = re.compile(
                global_config["error_ignore_stop"]
            )
        else:
            self.error_ignore_start_regex = None
            self.error_ignore_stop_regex = None

        if "warning_ignore_start" in global_config:
            self.warning_ignore_start_regex = re.compile(
                global_config["warning_ignore_start"]
            )
            self.warning_ignore_stop_regex = re.compile(
                global_config["warning_ignore_stop"]
            )
        else:
            self.warning_ignore_start_regex = None
            self.warning_ignore_stop_regex = None

        self.check_severity_is_warning = global_config["check_severity"] == "warning"

        self.verbose = ts_is_at_least_verbose()

        self.use_color = not global_config["no_color"]
        if self.use_color:
            self._to_text = lambda x: (
                f"{TsColors.GREEN}PASS{TsColors.END}"
                if x
                else f"{TsColors.RED}FAIL{TsColors.END}"
            )
        else:
            self._to_text = lambda x: "PASS" if x else "FAIL"

        # Initialize counters
        self.cnt_total_run_time = 0.0
        self.cnt_errors = 0
        self.cnt_warnings = 0
        self.cnt_ignored_errors = 0
        self.cnt_ignored_warnings = 0
        self.cnt_successes = 0
        self.cnt_total = 0

    @property
    def cnt_failures(self):
        return self.cnt_total - self.cnt_successes

    def __enter__(self):
        ts_info(TsInfoCode.GENERIC, "Test results:")
        self._print_test_result_header()
        return self

    def __exit__(self, *args):
        if args == (None, None, None):
            self._print_test_summary()

    def _prepare_regexes(self):
        """
        Fetches regular expressions for Warning, Error patterns
        and merge them into a single compiled regex
        """
        simulator = self.global_config["simulator"]

        for pattern_type in ("error_patterns", "warning_patterns"):
            patterns = self.global_config[pattern_type]

            regex_list = []
            for item in ("common", simulator):
                regex_list.extend(patterns.get(item, []))

            if regex_list:
                yield re.compile("|".join(regex_list))
            else:
                yield None

    def check_single_test(self, log_file_path: str):
        """
        Checks result of a single test.
        :param log_file_path: Simulation log file (TS_REPO_ROOT relative path)
        :return: Dictionary with following keys:
            'result' - True - Test passed, False - Test failed
            'warnings' - List of strings classified as warnings
            'errors' - List of strings classified as errors
        """
        if not os.path.exists(log_file_path):
            ts_throw_error(TsErrCode.ERR_SIM_1, log_file_path)

        # -- To improve performances we copy all the instance variables locally
        LINES_AFTER = self.LINES_AFTER

        UVM_IGNORE_START_PATTERN_REGEX = self.UVM_IGNORE_START_PATTERN_REGEX
        UVM_IGNORE_STOP_PATTERN_REGEX = self.UVM_IGNORE_STOP_PATTERN_REGEX

        errors_regex = self.errors_regex
        warnings_regex = self.warnings_regex

        uvm_is_enabled = self.uvm_is_enabled

        post_sim_msg_regex = self.post_sim_msg_regex

        error_ignore_start_regex = self.error_ignore_start_regex
        error_ignore_stop_regex = self.error_ignore_stop_regex

        warning_ignore_start_regex = self.warning_ignore_start_regex
        warning_ignore_stop_regex = self.warning_ignore_stop_regex

        check_severity_is_warning = self.check_severity_is_warning

        use_color = self.use_color
        # --

        uvm_report_summary_found = False
        __uvm_report_summary = False
        post_sim_msg_found = False
        __ignore_errors = False
        __ignore_warnings = False
        log_file_is_sim = os.path.basename(log_file_path).startswith("sim")

        # Expect test to 'pass' (return empty list)
        test_results = {
            "log_file_name": os.path.basename(log_file_path),
            "result": True,
            "errors": [],
            "warnings": [],
            "ignored_errors": [],
            "ignored_warnings": [],
            "sim_exit_code": 0,
            "run_time": None,
        }

        with open(log_file_path, encoding="latin-1") as fd:
            lines = fd.readlines()

        # Read additional information about the simulation from the log file
        ts_debug("Check that sim exit code is appended!")
        if len(lines) < 2 or self.LOG_TRAILER_REGEX.search(lines[-2]) is None:
            test_results["sim_exit_code"] = -1
            test_results["run_time"] = 0.0
        else:
            test_results["sim_exit_code"] = int(lines[-2].split()[1])
            test_results["run_time"] = float(lines[-1].split()[1])

        if test_results["sim_exit_code"] != 0:
            test_results["result"] = False
            test_results["errors"].append(
                {
                    "line_number": 0,
                    "line": "Simulation failed with exit code: {}".format(
                        test_results["sim_exit_code"]
                    ),
                }
            )
            if test_results["sim_exit_code"] == -1:
                test_results["errors"].append(
                    {
                        "line_number": 0,
                        "line": "Exit code -1 means that simulation exit code "
                        "was not written to log file properly!",
                    }
                )

        # Check errors and warnings for each line, appends match to results dictionary
        for line_number, line in enumerate(lines):

            # Ignore line if this latter belongs to the UVM report
            if uvm_is_enabled:
                if not uvm_report_summary_found:
                    if not __uvm_report_summary:
                        if UVM_IGNORE_START_PATTERN_REGEX.search(line):
                            ts_debug(f"Starting UVM ignore on line: '{line.strip()}'")
                            __uvm_report_summary = True
                            uvm_report_summary_found = True
                            continue
                else:
                    if __uvm_report_summary:
                        if UVM_IGNORE_STOP_PATTERN_REGEX.search(line):
                            ts_debug(f"Stopping UVM ignore on line: '{line.strip()}'")
                            __uvm_report_summary = False
                        continue

            # Look for post_sim_msg
            if (
                post_sim_msg_regex
                and not post_sim_msg_found
                and post_sim_msg_regex.search(line)
            ):
                post_sim_msg_found = True
                continue

            # Determine if errors have to be ignored
            if error_ignore_start_regex:
                if not __ignore_errors:
                    if error_ignore_start_regex.search(line):
                        ts_debug(
                            f"Starting error patterns ignore from line: '{line.strip()}'"
                        )
                        __ignore_errors = True
                        continue
                else:
                    if error_ignore_stop_regex.search(line):
                        ts_debug(
                            f"Stopping error patterns ignore from line: '{line.strip()}'"
                        )
                        __ignore_errors = False
                        continue

            # Determine if warnings have to be ignored
            if warning_ignore_start_regex:
                if not __ignore_warnings:
                    if warning_ignore_start_regex.search(line):
                        ts_debug(
                            f"Starting warning patterns ignore from line: '{line.strip()}'"
                        )
                        __ignore_warnings = True
                        continue
                else:
                    if warning_ignore_stop_regex.search(line):
                        ts_debug(
                            f"Stopping warning patterns ignore from line: '{line.strip()}'"
                        )
                        __ignore_warnings = False
                        continue

            # Look for patterns, errors first then warnings
            for severity, regex, ignore in (
                ("errors", errors_regex, __ignore_errors),
                ("warnings", warnings_regex, __ignore_warnings),
            ):
                if not regex:
                    continue
                match = regex.search(line)
                if match:
                    if use_color:
                        line = line.replace(
                            match.group(), TsColors.RED + match.group() + TsColors.END
                        )
                    log_line = {
                        "line": line,
                        "line_number": line_number,
                        "after_lines": lines[
                            line_number + 1 : line_number + 1 + LINES_AFTER
                        ],
                    }
                    if ignore:
                        test_results[f"ignored_{severity}"].append(log_line)
                    else:
                        test_results[severity].append(log_line)
                        if severity == "errors":
                            test_results["result"] = False
                        else:
                            # Warnings cause test to fail only when error severity is warning.
                            if check_severity_is_warning:
                                test_results["result"] = False
                    break

        # Check that both ignore errors and ignore warnings are not set at the end of the parsing
        if __ignore_errors or __ignore_warnings:
            test_results["result"] = False
            test_results["errors"].append(
                {
                    "line": "Simulation ended with ignoring errors and/or warnings! This is forbidden!",
                    "line_number": 0,
                }
            )

        # Check that post_sim_msg has been found, if defined beforehand
        if post_sim_msg_regex and not post_sim_msg_found:
            test_results["result"] = False
            test_results["errors"].append(
                {
                    "line": "Simulation ended without printing '{0}' into log. '{0}' is value "
                    "of 'post_sim_msg' keyword. If you set this keyword, testbench must print "
                    "this value to simulation log file, otherwise test will be marked "
                    "as failed!".format(post_sim_msg_regex.pattern),
                    "line_number": 0,
                }
            )

        # Make sure that UVM report summary has been found in a UVM test
        # UVM report summaries are only in simulation logs
        if log_file_is_sim and uvm_is_enabled and not uvm_report_summary_found:
            test_results["result"] = False
            test_results["errors"].append(
                {
                    "line": "UVM simulation ended without UVM report summary!",
                    "line_number": 0,
                }
            )

        # Update counters
        self.cnt_total_run_time += test_results["run_time"]
        self.cnt_errors += len(test_results["errors"])
        self.cnt_warnings += len(test_results["warnings"])
        self.cnt_ignored_errors += len(test_results["ignored_errors"])
        self.cnt_ignored_warnings += len(test_results["ignored_warnings"])
        if test_results["result"]:
            self.cnt_successes += 1
        self.cnt_total += 1

        # Print results
        self._print_test_result(test_results)

        # Return results
        return test_results

    def _print_test_result(self, test_results: dict):
        """
        Prints result of a single test.
        :param test_result: Results objet of single test
        """
        ts_print(
            self.RESULT_FORMAT.format(
                *map(
                    str,
                    (
                        test_results["log_file_name"],
                        "{:.1f}".format(test_results["run_time"]),
                        len(test_results["errors"]),
                        len(test_results["warnings"]),
                        len(test_results["ignored_errors"]),
                        len(test_results["ignored_warnings"]),
                        self._to_text(test_results["result"]),
                    ),
                )
            )
        )

        if self.verbose:
            for item in ("errors", "warnings", "ignored_errors", "ignored_warnings"):
                ts_print(f"List of {item.replace('_', ' ')}:", color=TsColors.PURPLE)
                for entry in test_results[item]:
                    ts_print(
                        f"Line {entry['line_number']}: {entry['line'].rstrip()}",
                        *map(lambda x: "\t" + x.rstrip(), entry.get("after_lines", [])),
                        sep="\n",
                    )

    def _print_test_result_header(self):
        """
        Prints test results header.
        """
        ts_print(
            self.SEPARATOR,
            self.RESULT_FORMAT.format(
                "Test log file",
                "Run-time",
                "Errors",
                "Warnings",
                "Ignored",
                "Ignored",
                "Result",
            ),
            self.RESULT_FORMAT.format("", "", "", "", "Errors", "Warnings", ""),
            self.SEPARATOR,
            sep="\n",
        )

    def _print_test_summary(self):
        """
        Prints test summary with total number of errors/warnings, passed/failed tests, etc.
        """
        ts_print(
            self.SEPARATOR,
            self.RESULT_FORMAT.format(
                *map(
                    str,
                    (
                        "Summary",
                        "{:.1f}".format(self.cnt_total_run_time),
                        self.cnt_errors,
                        self.cnt_warnings,
                        self.cnt_ignored_errors,
                        self.cnt_ignored_warnings,
                        "PASS: {}/{}".format(self.cnt_successes, self.cnt_total),
                    ),
                )
            ),
            self.SEPARATOR,
            sep="\n",
        )

def check_snps_log_file(flow_type, log_file_path: str) -> int:
    """
    Simple checker of synopsys DC and PT logs
    """
    with open(log_file_path, encoding="latin-1") as fd:
        lines = fd.readlines()

    errors = []
    warnings = []

    # DC and PT Error format is luckily simple enough that there is no need for regex
    for line_number, line in enumerate(lines):
        if (line.startswith("Error:") or line.startswith("[Error]")):
            errors.append([line_number, line])
        if (line.startswith("Warning:") or line.startswith("[Warning]")):
            warnings.append([line_number, line])

    if warnings:
        ts_print(f"{flow_type} log Warnings:", color=TsColors.ORANGE, big=True)
        for warning in warnings:
            tmp = warning[1].strip('\n')
            ts_print(f"Line {warning[0]}: {tmp}")
    else:
        ts_print(f"No warnings in {flow_type} log", color=TsColors.PURPLE, big=True)

    if errors:
        ts_print(f"{flow_type} log Errors:", color=TsColors.RED, big=True)
        for error in errors:
            tmp = error[1].strip('\n')
            ts_print(f"Line {error[0]}: {tmp}")
    else:
        ts_print(f"No errors in {flow_type} log", color=TsColors.PURPLE, big=True)

    # Fail if an error was detected
    return (len(errors) > 0)


