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


def __load_test_list(src: dict, path: str) -> list:
    """
    Loads list of tests.
    :param src: Source dictionary (content of list file or "test_group" keyword)
    :param path: List file path
    """
    ret_val = []
    for test in src["tests"]:
        if "name" in test:
            test["base_name"] = test["name"]

        # Interpret test which has "sub_list" keyword as sub-group!
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
    ts_debug(f"Loading test list file: {list_file_path}")

    list_file = load_yaml_file(list_file_path)
    ts_debug(f"Test list file is: {list_file}")

    ts_debug("Expanding environment variables of test list file")
    list_file = expand_vars(list_file)

    ts_debug("Checking list file for validity:")
    try:
        GRAMMAR_TST_LST.validate(list_file)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_SLF_18, e, list_file_path)
    ts_debug("List file valid!")

    for phase, options in (("elaboration", "elab_options"),
                            ("simulation", "sim_options")):
        ts_debug(f"Merging {phase} options in test file")
        root_options = list_file.pop(options, {})
        for k, v in root_options.items():
            for test_dict in list_file["tests"]:
                test_options = test_dict.setdefault(options, {})
                if k in test_options:
                    test_options[k] = v + " " + test_options[k]
                else:
                    test_options[k] = v
        ts_debug("Done")

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
    regex = re.compile(
        "^("
        + "|".join(x.replace("*", ".*") for x in test_names)
        + ")$"
    )

    ts_debug(f"Test regex: {regex.pattern}")

    TsGlobals.TS_TEST_RUN_LIST = [
        test for test in TsGlobals.TS_TEST_LIST
        if regex.match(test["name"])
    ]

    ts_debug(f"Chosen tests are: {TsGlobals.TS_TEST_RUN_LIST}")

    return TsGlobals.TS_TEST_RUN_LIST


def get_test(test_name: str, test_list: list) -> dict:
    """
    Obtains test dictionary by name from list of tests.
    :param test_name: Name of the test to obtain
    :param test_list: List of tests from which to obtain the test dictionary
    """
    try:
        return [*filter(lambda x: x["name"] == test_name, test_list)][0]
    except IndexError:
        ts_script_bug(f"Could not find test '{test_name}'")


def get_test_list(test_list: list, get_repeat: bool = False) -> list:
    """
    Prints flat list of tests
    :param test_list: List of tests to print.
    :param get_repeat: get number of iteration for each test
    """
    list_to_print = []
    for test in test_list:
        ts_debug(test)
        if get_repeat:
            list_to_print.append(f"{test['name']} x {test['regress_loops']} time(s)")
        else:
            list_to_print.append(test["name"])
    return list_to_print

def check_test(test_name: str):
    if not test_name in get_test_list(TsGlobals.TS_TEST_LIST):
        ts_throw_error(TsErrCode.GENERIC, "Invalid test name {}.".format(test_name))
