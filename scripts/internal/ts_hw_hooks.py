# -*- coding: utf-8 -*-

####################################################################################################
# Hooks to be called within simulation system
#
# TODO: License
####################################################################################################

import os
from enum import Enum, auto

from .ts_hw_global_vars import *
from .ts_hw_logging import *
from .ts_hw_common import *


class TsHooks(Enum):
    PRE_COMPILE = auto()
    POST_COMPILE = auto()
    PRE_RUN = auto()
    PRE_TEST = auto()
    PRE_TEST_SPECIFIC = auto()
    PRE_SIM = auto()
    POST_TEST_SPECIFIC = auto()
    POST_TEST = auto()
    POST_RUN = auto()
    POST_CHECK = auto()


__HOOK_DICT = {
    TsHooks.PRE_COMPILE: "pre_compile_hook",
    TsHooks.POST_COMPILE: "post_compile_hook",
    TsHooks.PRE_RUN: "pre_run_hook",
    TsHooks.PRE_TEST: "pre_test_hook",
    TsHooks.PRE_TEST_SPECIFIC: "pre_test_hook",
    TsHooks.PRE_SIM: "pre_sim_hook",
    TsHooks.POST_TEST_SPECIFIC: "post_test_hook",
    TsHooks.POST_TEST: "post_test_hook",
    TsHooks.POST_RUN: "post_run_hook",
    TsHooks.POST_CHECK: "post_check_hook",
}


def __call_hook(hook: TsHooks, root_dict: dict, *args):
    """
    Internal hook call function.
    :param hook: Type of hook
    :param root_dict: Configuration dictionary which contains the hook keyword.
    :param args: Optional arguments to be passed to hook if specified.
    """
    hook_type = __HOOK_DICT[hook]
    ts_debug("Attempting to run hook: {}".format(hook_type))

    ts_debug(str(root_dict))
    # Some checks
    try:
        hook_path = root_dict[hook_type]
    except KeyError:
        # Skip if hook is not specified!
        ts_info(TsInfoCode.INFO_HOK_1, hook_type)
        return

    ts_info(TsInfoCode.INFO_HOK_0, hook_type)

    abs_hook_path = ts_get_root_rel_path(hook_path)

    # If hook does not exist, try to execute it on system console
    if not os.path.isfile(abs_hook_path):
        ts_info(TsInfoCode.INFO_GENERIC, f"File '{abs_hook_path}' does not exist, hook '{hook_path}' will be executed as bash command...")
        if os.system(hook_path) >> 8 != 0:
            ts_throw_error(TsErrCode.ERR_HOK_0, hook_path, hook_type)

    # Or execute it with optional arguments
    else:
        hook_cmd = "source {} {}".format(abs_hook_path, " ".join(map(str, args)))
        ts_debug("Hook_command: {}".format(hook_cmd))
        os.system(hook_cmd)


def ts_call_global_hook(hook: TsHooks, *args):
    """
    Call hook in simulation scripting system.
    :param hook: Type of hook.
    :param args: Optional arguments to be passed to hook if specified.
    """
    __call_hook(hook, ts_get_cfg(), *args)


def ts_call_local_hook(hook: TsHooks, local_dict: dict, *args):
    """
    Call hook in simulation scripting system.
    :param hook: Type of hook
    :param local_dict: Local dictionary with hook keyword in it.
    :param args: Optional arguments to be passed to hook if specified.
    """
    __call_hook(hook, local_dict, *args)

