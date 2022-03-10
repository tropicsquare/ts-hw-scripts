# -*- coding: utf-8 -*-

####################################################################################################
# Grammar for simulation config file, source list file and test list file.
#
# TODO: License
####################################################################################################


####################################################################################################
# Common grammar
####################################################################################################

import contextlib
#https://github.com/keleshev/schema
from schema import Schema, And, Regex, Optional, Or, Use

from .ts_hw_common import *
from .ts_hw_logging import *


###################################################################################################
#
# Common error/warning patterns
#
###################################################################################################


BUILT_IN_PATTERNS = {
    "error_patterns": {
        "common": [
            "UVM_ERROR",
            "UVM_FATAL"
        ],
        "vcs": [
            # Produced by $error, $fatal
            "Error:",
            "Fatal:",

            # Produced by failing "assert property" in SystemVerilog!
            "failed at",

            # Produced by report severity error/fatal in VHDL
            "Report ERROR",
            "Report FAILURE",

            # Produced by timing violations in standard cells
            "Timing violation"
        ]
    },
    "warning_patterns": {
        "common": [
            "UVM_WARNING",
        ],
        "vcs": [
            "Warning:",
            "Report WARNING"
        ]
    }
}

BUILT_IN_UVM_IGNORE_START_PATTERN = "--- UVM Report (catcher )?Summary ---"
BUILT_IN_UVM_IGNORE_STOP_PATTERN = "\*\* Report counts by id"


###################################################################################################
#
# GRAMMAR
#
###################################################################################################


class GrammarSchema(Schema):
    """
    Schema with iterator
    """

    def __iter__(self):
        for i in self.schema:
            if isinstance(i, Schema):
                yield i.schema
            else:
                yield i


class VerboseOptional(Optional):

    def __init__(self, key, *args, **kwargs):
        default = kwargs["default"]
        def wrapper():
            ts_throw_warning(TsWarnCode.WARN_CFG_1, key, default)
            return default
        kwargs["default"] = wrapper
        super().__init__(key, *args, **kwargs)


# Error/Warning patterns dictionary
class Patterns:

    schema = Or(
        None,
        {
            Optional("common"): Or(None, [str]),
            Optional("vcs"): Or(None, [str])
        }
    )

    def __init__(self, patterns):
        self.patterns = patterns

    def validate(self, value):
        return_value = self.schema.validate(value)
        # Merge dictionary with builtin patterns
        for k in BUILT_IN_PATTERNS[self.patterns]:
            if not isinstance(return_value.get(k), list):
                return_value[k] = []
            return_value[k].extend(BUILT_IN_PATTERNS[self.patterns][k])
        return return_value


__yaml_file_regex = Regex('.*\.yml')

__sim_time_res_regex = Regex('[munpf]?s')

__key_val_dict = {str: Or(None, str, int, float, bool)}

# Allowed simulator specific compile options. See format below.
__simulator_comp_sim_elab_opts = {
    Or("common", "vcs"): str,
}

__verbosity_options = Or(
    None,
    {
        Optional("elab_options"): __simulator_comp_sim_elab_opts,
        Optional("sim_options"): __simulator_comp_sim_elab_opts,
        Optional("generics"): __key_val_dict,
        Optional("parameters"): __key_val_dict
    }
)


###################################################################################################
#
# Simulation config file grammar
#
# These are allowed key-words within configuration file and/or command line options. Note that
# when using multi-word keyword, command line option separates words with '-' while config file
# separates them with '_'. It is a rule to always separate options internally by '_'.
#
# Allowed attributes are used in following format:
#   1. Key represents key in config file
#   2. String value -> Interpreted as regex. If matches, then allowed
#   3. Tuple -> Interpreted as group of allowed string values. Not matched as regex!
#   4. List -> Interpreted as list of sub-items (as if YAML list)
#   5. Dictionary -> Represents named sub-level of hierarchy
#   6. "bool" -> Indicates that boolean value shall be present
###################################################################################################
GRAMMAR_SIM_CFG = GrammarSchema({
    "simulator": lambda x: x in ("vcs"),
    VerboseOptional("vhdl_std", default="vhdl08"): lambda x: x in ("vhdl87", "vhdl93", "vhdl02", "vhdl08"),
    VerboseOptional("verilog_std", default="v01"): lambda x: x in ("v95", "v01", "v05"),
    Optional("coverage", default=False): bool,
    Optional("gui", default=None): lambda x: x in (None, "dve", "verdi"),
    Optional("script_debug", default=False): bool,
    Optional("compile_debug", default=False): bool,
    Optional("verbose", default=False): bool,
    Optional("very_verbose", default=False): bool,
    Optional("no_color", default=False): bool,
    Optional("seed"): int,
    "target": str,
    Optional("test_name_strategy", default=None): lambda x: x in (None, "uvm", "generic_parameter"),
    Optional("test_name_generic"): str,
    Optional("test_name_parameter"): str,
    Optional("clear", default=False): bool,
    Optional("clear_logs", default=False): bool,
    Optional("no_sim_out", default=False): bool,
    Optional("no_check", default=False): bool,
    Optional("check_elab_log", default=False): bool,
    Optional("recompile", default=False): bool,
    Optional("loop", default=1): int,
    Optional("dump_waves", default=False): bool,
    Optional("enable_uvm", default=False): bool,
    Optional("simulation_resolution"): __sim_time_res_regex,
    Optional("session_file"): And(str, Use(ts_get_curr_dir_rel_path), os.path.isfile),
    Optional("do_file"): And(str, Use(ts_get_curr_dir_rel_path), os.path.isfile),
    Optional("generics"): __key_val_dict,
    Optional("parameters"): __key_val_dict,
    Optional("license_wait", default=False): bool,
    Optional("define"): __key_val_dict,
    Optional("regress_jobs", default=1): int,
    VerboseOptional("timestamp_log_file", default=True): bool,
    VerboseOptional("check_severity", default="warning"): lambda x: x in ("warning", "error"),
    VerboseOptional("stop_severity", default="failure"): lambda x: x in ("note", "warning", "error", "failure", "nostop"),
    Optional("comp_options"): __simulator_comp_sim_elab_opts,
    Optional("add_comp_options"): str,
    Optional("add_vhdl_comp_options"): str,
    Optional("add_verilog_comp_options"): str,
    Optional("elab_options"): __simulator_comp_sim_elab_opts,
    Optional("add_elab_options"): str,
    Optional("sim_options"): __simulator_comp_sim_elab_opts,
    Optional("add_sim_options"): str,
    Optional("test_list_file"): __yaml_file_regex,
    Optional("build_dir", default=ts_get_root_rel_path(TsGlobals.TS_SIM_BUILD_PATH)): str,
    Optional("include_dirs"): Or(str, [str]),
    Optional("pre_compile_hook"): str,
    Optional("post_compile_hook"): str,
    Optional("pre_run_hook"): str,
    Optional("pre_test_hook"): str,
    Optional("pre_sim_hook"): str,
    Optional("post_test_hook"): str,
    Optional("post_run_hook"): str,
    Optional("post_check_hook"): str,
    # Fill value as empty value will match and the test won't fail!
    VerboseOptional("post_sim_msg", default=""): str,
    "targets": {
        str: {
            Optional("inherits"): str,
            "source_list_files": Or(str, [str]),
            "top_entity": str,
            Optional("test_list_file"): __yaml_file_regex,
            Optional("comp_options"): __simulator_comp_sim_elab_opts,
            Optional("sim_options"): __simulator_comp_sim_elab_opts,
            Optional("elab_options"): __simulator_comp_sim_elab_opts,
            Optional("generics"): __key_val_dict,
            Optional("parameters"): __key_val_dict,
            Optional("define"): __key_val_dict,
            Optional("enable_uvm", default=False): bool,
            Optional("test_name_strategy", default=None): lambda x: x in (None, "uvm", "generic_parameter"),
            Optional("test_name_generic"): str,
            Optional("test_name_parameter"): str,
            Optional("include_dirs"): Or(str, [str])
        }
    },
    Optional("error_patterns", default=BUILT_IN_PATTERNS["error_patterns"]): Patterns("error_patterns"),
    Optional("warning_patterns", default=BUILT_IN_PATTERNS["warning_patterns"]): Patterns("warning_patterns"),
    Optional("error_ignore_start"): str,
    Optional("error_ignore_stop"): str,
    Optional("warning_ignore_start"): str,
    Optional("warning_ignore_stop"): str,
    Optional("sim_verbosity_levels", default={"info": {}}): {
        Optional("debug"): __verbosity_options,
        Optional("info"): __verbosity_options,
        Optional("warning"): __verbosity_options,
        Optional("error"): __verbosity_options
    },
    VerboseOptional("sim_verbosity", default="info"): lambda x: x in ("debug", "info", "warning", "error")
})


###################################################################################################
#
# Source list file grammar
# 
###################################################################################################
GRAMMAR_SRC_LST = GrammarSchema({
    Optional("define"): __key_val_dict,
    "library": str,
    Optional("include_dirs"): Or(str, [str]),
    "source_list": [{
        "file": str,
        Optional("path"): str,
        Optional("library"): str,
        Optional("comp_options"): __simulator_comp_sim_elab_opts,
        Optional("include_dirs"): Or(str, [str]),
        Optional("define"): __key_val_dict,
    }]
})


###################################################################################################
#
# Test list file grammar
# 
###################################################################################################


GRAMMAR_TST_LST = GrammarSchema({
    "tests": [{
        Or("name", "sub_list"): str,
        Optional("elab_options"): __simulator_comp_sim_elab_opts,
        Optional("sim_options"): __simulator_comp_sim_elab_opts,
        Optional("pre_test_hook"): str,
        Optional("post_test_hook"): str,
        Optional("generics"): __key_val_dict,
        Optional("parameters"): __key_val_dict,
        Optional("regress_loops"): int,
    }]
})

