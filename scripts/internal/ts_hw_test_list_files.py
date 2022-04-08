# -*- coding: utf-8 -*-

####################################################################################################
# Functions for loading test list files.
#
# TODO: License
####################################################################################################

import os
import re
import contextlib
from schema import SchemaError

from .ts_hw_common import *
from .ts_grammar import *


def __check_test_list_file(list_file: dict, path: str):
    """
    Checks if test list file is valid. Includes check of allowed keywords as well as required
    keywords.
    :param list_file: Dictionary with loaded test list file
    :param path: Path to test list file.
    """
    try:
        GRAMMAR_TST_LST.validate(list_file)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_SLF_18, e, path)

    for test_item in list_file["tests"]:
        with contextlib.suppress(KeyError):
            check_valid_test_name(test_item["name"], path)


def __load_test_list(src: dict, path: str) -> list:
    """
    Loads list of tests.
    :param src: Source dictionary (content of list file or "test_group" keyword)
    :param path: List file path
    """
    ret_val = []
    for test in src["tests"]:
        # Interpret test which has "sub-list" keyword as sub-group!
        with contextlib.suppress(KeyError):
            sub_list_path = ts_get_file_rel_path(path, test["sub_list"])
            ts_debug("Loading SUB test list!")
            sub_test_list = __load_test_list_file(sub_list_path)

            # If name is defined, then tests from sub-list create a new group
            with contextlib.suppress(KeyError):
                for sub_test in sub_test_list:
                    sub_test["name"] = f"{test['name']}.{sub_test['name']}"

            ret_val.extend(sub_test_list)
            continue

        for hook_name in ("pre_test_hook", "post_test_hook"):
            tmp_path = ts_get_file_rel_path(path, test.get(hook_name, ''))
            if os.path.isfile(tmp_path):
                test[hook_name] = tmp_path
        ret_val.append(test)

    return ret_val


def __load_test_list_file(list_file_path: str) -> list:
    """
    Loads test list file.
    :param list_file_path: Path to test list file
    """
    check_list_file_present(list_file_path)
    ts_info(TsInfoCode.INFO_CMN_15, list_file_path)

    try:
        with open(list_file_path) as lf:
            list_file = yaml.safe_load(lf)
    except Exception as e:
        ts_throw_error(TsErrCode.ERR_SLF_1, list_file_path)

    ts_debug(f"Test list file is: {list_file}")

    __check_test_list_file(list_file, list_file_path)

    # Load list of tests
    ts_debug("Getting list of tests...")
    return __load_test_list(list_file, list_file_path)


def load_tests():
    """
    Loads test from root list file and sub-list files.
    """    

    TsGlobals.TS_TEST_LIST = []
    for cfg in (ts_get_cfg(), ts_get_cfg("targets")[ts_get_cfg("target")]):
        list_file = ts_get_root_rel_path(cfg.get("test_list_file", ''))
        if os.path.isfile(list_file):
            TsGlobals.TS_TEST_LIST.extend(__load_test_list_file(list_file))


def get_tests_to_run(test_names: list) -> list:
    """
    Creates list of tests to be executed from 'test names' passed from command line. Uses unix
    like star completion.
    :param test_names: List of test names to be queried, may contain wild-cards.
    """
    test_list = []

    for test_name in test_names:
        regex_pat = test_name.replace('*', '.*')
        regex_pat = "^" + regex_pat + "$"
        ts_debug("Test regex: {}".format(regex_pat))
        for available_test in TsGlobals.TS_TEST_LIST:
            if re.match(regex_pat, available_test["name"]):
                test_list.append(available_test)

    ts_debug(f"Chosen tests are: {test_list}")
    TsGlobals.TS_TEST_RUN_LIST = test_list

    return test_list


def get_test(test_name: str, test_list: list):
    """
    Obtains test dictionary by name from list of tests.
    :param test_name: Name of the test to obtain
    :param test_list: List of tests from which to obtain the test dictionary
    """
    for test in test_list:
        if test["name"] == test_name:
            return test

    ts_script_bug("Could not find test '{}'".format(test_name))


def print_test_list(test_list: list, print_repeat: bool = False):
    """
    Prints flat list of tests
    :param test_list: List of tests to print.
    """
    for test in test_list:
        if print_repeat:
            print("     {} x {} times".format(test["name"], test["regress_loops"]))
        else:
            print("     {}".format(test["name"]))

    for test in test_list:
        ts_debug(test)


def print_test_iterations():
    """
    Prints info about '--loop' option.
    """
    ts_info(TsInfoCode.INFO_GENERIC, "Each test will be executed {} times".format(
            ts_get_cfg("loop")))

