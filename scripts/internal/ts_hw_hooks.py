# -*- coding: utf-8 -*-

####################################################################################################
# Hooks to be called within simulation system
#
# For license see LICENSE file in repository root.
####################################################################################################

import os
from enum import Enum

from .ts_hw_common import exec_cmd_in_dir, ts_get_cfg, ts_get_root_rel_path
from .ts_hw_logging import TsErrCode, TsInfoCode, ts_debug, ts_info, ts_throw_error


class TsHooks(str, Enum):
    PRE_COMPILE = "pre_compile_hook"
    POST_COMPILE = "post_compile_hook"
    PRE_RUN = "pre_run_hook"
    PRE_TEST = "pre_test_hook"
    PRE_TEST_SPECIFIC = "pre_test_hook"
    PRE_SIM = "pre_sim_hook"
    POST_TEST_SPECIFIC = "post_test_hook"
    POST_TEST = "post_test_hook"
    POST_RUN = "post_run_hook"
    POST_CHECK = "post_check_hook"


def __call_hook(hook: TsHooks, root_dict: dict, *args):
    """
    Internal hook call function.
    :param hook: Type of hook
    :param root_dict: Configuration dictionary which contains the hook keyword.
    :param args: Optional arguments to be passed to hook if specified.
    """
    hook_type = hook.value
    ts_debug(f"Attempting to run hook: '{hook_type}'")

    # Some checks
    try:
        hook_path = root_dict[hook_type]
    except KeyError:
        # Skip if hook is not specified!
        ts_info(TsInfoCode.INFO_HOK_1, hook_type)
        return

    ts_info(TsInfoCode.INFO_HOK_0, hook_type)
    ts_debug(root_dict)

    abs_hook_path = ts_get_root_rel_path(hook_path)

    # If hook does not exist, try to execute it on system console
    if not os.path.isfile(abs_hook_path):
        ts_debug(
            f"File '{abs_hook_path}' does not exist, "
            f"hook '{hook_path}' will be executed as bash command..."
        )
        if exec_cmd_in_dir(
            directory=os.getcwd(),
            command=hook_path,
            batch_mode=True) != 0:
            ts_throw_error(TsErrCode.ERR_HOK_0, hook_path, hook_type)

    # Or execute it with optional arguments
    else:
        hook_cmd = f"source {abs_hook_path} {' '.join(map(str, args))}"
        ts_debug(f"Hook_command: {hook_cmd}")
        exec_cmd_in_dir(
            directory=os.getcwd(),
            command=hook_cmd,
            batch_mode=True
        )


def ts_call_global_hook(hook: TsHooks, *args):
    """
    Call hook in simulation scripting system.
    :param hook: Type of hook.
    :param args: Optional arguments to be passed to hook if specified.
    """
    ts_debug("Calling global hook")
    __call_hook(hook, ts_get_cfg(), *args)


def ts_call_local_hook(hook: TsHooks, local_dict: dict, *args):
    """
    Call hook in simulation scripting system.
    :param hook: Type of hook
    :param local_dict: Local dictionary with hook keyword in it.
    :param args: Optional arguments to be passed to hook if specified.
    """
    ts_debug("Calling local hook")
    __call_hook(hook, local_dict, *args)
