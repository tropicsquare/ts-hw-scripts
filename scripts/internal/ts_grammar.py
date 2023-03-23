# -*- coding: utf-8 -*-

####################################################################################################
# Grammar for simulation config file, source list file and test list file.
#
# TODO: License
####################################################################################################


####################################################################################################
# Common grammar
####################################################################################################
import os

from schema import And, Optional, Or, Regex, Schema, SchemaError, Use

from .ts_hw_common import ts_get_curr_dir_rel_path, ts_get_root_rel_path
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsColors,
    TsErrCode,
    TsWarnCode,
    ts_debug,
    ts_print,
    ts_throw_error,
    ts_warning,
)

###################################################################################################
#
# Common error/warning patterns
#
###################################################################################################


BUILT_IN_PATTERNS = {
    "error_patterns": {
        "common": ["UVM_ERROR", "UVM_FATAL"],
        "vcs": [
            # Produced by $error, $fatal
            "Error:",
            "Fatal:",
            # Produced by elaboration of VCS
            "Error-",
            # Produced by failing "assert property" in SystemVerilog!
            "failed at",
            # Produced by report severity error/fatal in VHDL
            "Report ERROR",
            "Report FAILURE",
            # Produced by timing violations in standard cells
            "Timing violation",
            # Produced by VHDLs assert
            "Assertion ERROR",
        ],
    },
    "warning_patterns": {
        "common": [
            "UVM_WARNING",
        ],
        "vcs": [
            "Warning:",
            "Report WARNING",
            # Produced by elaboration of VCS
            "Warning-",
        ],
    },
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
            ts_warning(TsWarnCode.WARN_CFG_1, key, default)
            return default

        kwargs["default"] = wrapper
        super().__init__(key, *args, **kwargs)


# Error/Warning patterns dictionary
class Patterns:

    schema = GrammarSchema({Optional("common"): [str], Optional("vcs"): [str]})

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


# Define a set of values the challenged value should be a part of
class Among:
    def __init__(self, *choices):
        self.choices = set(choices)

    def validate(self, value):
        if not value in self.choices:
            raise SchemaError(f"Bad value '{value}'; should be among {self.choices}")
        return value


_yaml_file_regex = Regex(".*\.yml")

_sim_time_res_regex = Regex("[munpf]?s")

_key_val_dict = {str: Or(None, str, int, float, bool)}

# Allowed simulator specific compile options. See format below.
_simulator_comp_sim_elab_opts = {
    Or("common", "vcs"): str,
}

_verbosity_options = GrammarSchema(
    {
        Optional("elab_options"): _simulator_comp_sim_elab_opts,
        Optional("sim_options"): _simulator_comp_sim_elab_opts,
        Optional("generics"): _key_val_dict,
        Optional("parameters"): _key_val_dict,
    }
)


###################################################################################################
#
# Simulation config file grammar
#
###################################################################################################
class GRAMMAR_SIM_CFG:
    """
    This class is used to check the validity of the simulation configuration file
    """

    schema = GrammarSchema(
        {
            "simulator": Among("vcs"),
            VerboseOptional("vhdl_std", default="vhdl08"): Among(
                "vhdl87", "vhdl93", "vhdl02", "vhdl08"
            ),
            VerboseOptional("verilog_std", default="v01"): Among("v95", "v01", "v05"),
            Optional("coverage", default=False): bool,
            # gui causes problems in other flows, please do not use it this way
            # Optional("gui", default=None): Among(None, "dve", "verdi"),
            Optional("compile_debug", default=False): bool,
            Optional("verbose", default=0): int,
            Optional("fail_fast", default=False): bool,
            Optional("no_color", default=False): bool,
            Optional("seed"): int,
            Optional("target"): str,
            Optional("test_name_strategy", default=None): Among(
                None, "uvm", "generic_parameter"
            ),
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
            Optional("simulation_resolution"): _sim_time_res_regex,
            Optional("session_file", default=None): And(
                str, Use(ts_get_curr_dir_rel_path), os.path.isfile
            ),
            Optional("do_file"): And(str, Use(ts_get_root_rel_path), os.path.isfile),
            Optional("generics"): _key_val_dict,
            Optional("parameters"): _key_val_dict,
            Optional("license_wait", default=False): bool,
            Optional("define"): _key_val_dict,
            Optional("regress_jobs", default=1): int,
            VerboseOptional("timestamp_log_file", default=True): bool,
            VerboseOptional("check_severity", default="warning"): Among(
                "warning", "error"
            ),
            VerboseOptional("stop_severity", default="failure"): Among(
                "note", "warning", "error", "failure", "nostop"
            ),
            Optional("comp_options"): _simulator_comp_sim_elab_opts,
            Optional("add_comp_options", default=""): str,
            Optional("add_vhdl_comp_options", default=""): str,
            Optional("add_verilog_comp_options", default=""): str,
            Optional("elab_options"): _simulator_comp_sim_elab_opts,
            Optional("add_elab_options", default=""): str,
            Optional("sim_options"): _simulator_comp_sim_elab_opts,
            Optional("add_sim_options", default=""): str,
            Optional("test_list_file"): And(
                _yaml_file_regex, Use(ts_get_root_rel_path), os.path.isfile
            ),
            Optional(
                "build_dir", default=ts_get_root_rel_path(TsGlobals.TS_SIM_BUILD_PATH)
            ): str,
            Optional("include_dirs"): [str],
            Optional("pre_compile_hook"): str,
            Optional("post_compile_hook"): str,
            Optional("pre_run_hook"): str,
            Optional("pre_test_hook"): str,
            Optional("pre_sim_hook"): str,
            Optional("post_test_hook"): str,
            Optional("post_run_hook"): str,
            Optional("post_check_hook"): str,
            Optional("post_sim_msg"): str,
            "targets": {
                str: {
                    Optional("inherits"): str,
                    "source_list_files": [str],
                    "top_entity": Regex("^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)?$"),
                    Optional("test_list_file"): And(
                        _yaml_file_regex, Use(ts_get_root_rel_path), os.path.isfile
                    ),
                    Optional("comp_options"): _simulator_comp_sim_elab_opts,
                    Optional("sim_options"): _simulator_comp_sim_elab_opts,
                    Optional("elab_options"): _simulator_comp_sim_elab_opts,
                    Optional("generics"): _key_val_dict,
                    Optional("parameters"): _key_val_dict,
                    Optional("define"): _key_val_dict,
                    Optional("enable_uvm", default=False): bool,
                    Optional("test_name_strategy", default=None): Among(
                        None, "uvm", "generic_parameter"
                    ),
                    Optional("test_name_generic"): str,
                    Optional("test_name_parameter"): str,
                    Optional("include_dirs"): [str],
                    Optional("do_file"): And(
                        str, Use(ts_get_root_rel_path), os.path.isfile
                    ),
                }
            },
            Optional(
                "error_patterns", default=BUILT_IN_PATTERNS["error_patterns"]
            ): Patterns("error_patterns"),
            Optional(
                "warning_patterns", default=BUILT_IN_PATTERNS["warning_patterns"]
            ): Patterns("warning_patterns"),
            Optional("error_ignore_start"): str,
            Optional("error_ignore_stop"): str,
            Optional("warning_ignore_start"): str,
            Optional("warning_ignore_stop"): str,
            Optional("sim_verbosity_levels", default={"info": {}}): {
                Optional("debug"): _verbosity_options,
                Optional("info"): _verbosity_options,
                Optional("warning"): _verbosity_options,
                Optional("error"): _verbosity_options,
            },
            VerboseOptional("sim_verbosity", default="info"): Among(
                "debug", "info", "warning", "error"
            ),
        }
    )

    @classmethod
    def attrs(cls):
        return iter(cls.schema)

    @classmethod
    def validate(cls, value):
        value = cls.schema.validate(value)

        ts_debug("Checking test strategy parameters")
        for to_test in (value, *value["targets"].values()):
            if to_test.get("test_name_strategy") == "generic_parameter":
                if (
                    to_test.get("test_name_generic"),
                    to_test.get("test_name_parameter"),
                ) == (None, None):
                    raise SchemaError(
                        "When 'test_name_strategy=generic_parameter', either "
                        "'test_name_generic' (in VHDL top) "
                        "or 'test_name_parameter' (in Verilog /System Verilog top) "
                        "must be defined and contain top level generic/parameter name."
                    )

        ts_debug("Checking coupling of 'ignore_start' and 'ignore_stop' patterns")
        config_keys = set(value.keys())
        for kwd_pair in (
            {"error_ignore_start", "error_ignore_stop"},
            {"warning_ignore_start", "warning_ignore_stop"},
        ):
            if len(kwd_pair - config_keys) == 1:
                raise SchemaError(
                    "'{}' and '{}' keywords in config file must be set together! "
                    "It is not possible to set one without the other!".format(*kwd_pair)
                )

        return value


###################################################################################################
#
# Source list file grammar
#
###################################################################################################
class GRAMMAR_SRC_LST:
    """
    This class is used to check the validity of a source list file
    """

    schema = GrammarSchema(
        {
            Optional("define"): _key_val_dict,
            "library": str,
            Optional("include_dirs"): [str],
            Optional("comp_options"): _simulator_comp_sim_elab_opts,
            "source_list": [
                {
                    "file": str,
                    Optional("path"): str,
                    Optional("library"): str,
                    Optional("lang"): Among("vhdl", "verilog", "system_verilog"),
                    Optional("comp_options"): _simulator_comp_sim_elab_opts,
                    Optional("include_dirs"): [str],
                    Optional("define"): _key_val_dict,
                }
            ],
        }
    )

    @classmethod
    def validate(cls, value):
        cls.schema.validate(value)

        ts_debug("Enforcing absence of 'define' keyword in VHDL files")
        for file_dict in value["source_list"]:
            if "define" in file_dict and file_dict["file"].endswith(".vhd"):
                raise SchemaError(
                    f"File '{file_dict['file']}' is a VHDL file "
                    "and thus does not support 'define' keyword!"
                )


###################################################################################################
#
# Test list file grammar
#
###################################################################################################
class GRAMMAR_TST_LST:
    """
    This class is used to check the validity of a test list file
    """

    schema = GrammarSchema(
        {
            Optional("elab_options"): _simulator_comp_sim_elab_opts,
            Optional("sim_options"): _simulator_comp_sim_elab_opts,
            "tests": [
                {
                    Or("name", "sub_list"): str,
                    Optional("elab_options"): _simulator_comp_sim_elab_opts,
                    Optional("sim_options"): _simulator_comp_sim_elab_opts,
                    Optional("pre_test_hook"): str,
                    Optional("post_test_hook"): str,
                    Optional("generics"): _key_val_dict,
                    Optional("parameters"): _key_val_dict,
                    Optional("regress_loops"): int,
                }
            ],
        }
    )

    test_name_forbidden_characters = set("[@!#$%^&*()<>?/\|}{~:]")

    @classmethod
    def validate(cls, value):
        cls.schema.validate(value)

        test_names = [
            *map(lambda x: x["name"], filter(lambda x: x.get("name"), value["tests"]))
        ]

        ts_debug("Check uniqueness of test names")
        count = {}
        for test_name in test_names:
            count.setdefault(test_name, 0)
            count[test_name] += 1
        duplicated_names = [(k, v) for k, v in count.items() if v > 1]
        if duplicated_names:
            raise SchemaError(f"Some tests have duplicates: {duplicated_names}")

        ts_debug("Check test names validity")
        for test_name in test_names:
            unauthorized_characters = (
                set(test_name) & cls.test_name_forbidden_characters
            )
            if unauthorized_characters:
                raise SchemaError(
                    f"invalid test name '{test_name}' contains "
                    f"unauthorized character(s) '{unauthorized_characters}'."
                )


###################################################################################################
#
# PDK config file grammar
#
###################################################################################################

# Corner name : Corner path
__corner_view_config = GrammarSchema({str: str})

# Single path, or multiple files (e.g. lefs can be split to multiple files for single PDK std celss)
__str_or_list = GrammarSchema(Or(str, list))

PDK_VIEW_CONFIG = GrammarSchema(
    {
        Optional("nldm_db"): __corner_view_config,
        Optional("nldm_lib"): __corner_view_config,
        Optional("ccs_db"): __corner_view_config,
        Optional("ccs_lib"): __corner_view_config,
        Optional("lef"): __str_or_list,
        Optional("def"): __str_or_list,
        Optional("gds"): __str_or_list,
        Optional("cdl"): __str_or_list,
        Optional("milkyway"): str,
        Optional("slf"): __str_or_list,
    }
)

__GRAMMAR_VERSION = GrammarSchema(Or(str, int, float))

GRAMMAR_PDK_CONFIG = GrammarSchema(
    {
        "name": str,
        Optional("corners"): {
            str: Or(
                None,
                {
                    Optional("voltage"): float,
                    Optional("temperature"): int,
                    Optional("parasitics"): int,
                },
            ),
        },
        Optional("std_cells"): [
            {
                "name": str,
                Optional("vendor"): str,
                "version": __GRAMMAR_VERSION,
                Optional("opcond"): __corner_view_config,
                "views": PDK_VIEW_CONFIG,
            }
        ],
        Optional("ips"): [
            {
                "name": str,
                Optional("vendor"): str,
                "version": __GRAMMAR_VERSION,
                Optional("opcond"): __corner_view_config,
                "views": PDK_VIEW_CONFIG,
            }
        ],
    }
)


###################################################################################################
#
# Design config file grammar
#
###################################################################################################

__mode_usage_config = lambda s: s in (
    "sim",
    "syn",
    "sta",
    "dft-lint",
    "dft-atpg",
    "pnr",
    "pwr",
    "sta-signoff",
)


GRAMMAR_DSG_CONFIG = GrammarSchema(
    {
        "pdk_configs": [str],
        "design": {
            "target": str,
            Optional("flow_dirs"): {
                Optional("sim"): str,
                Optional("syn"): str,
                Optional("dft-lint"): str,
                Optional("sta"): str,
                Optional("pnr"): str,
                Optional("pwr"): str,
            },
            "pdk": str,
            "std_cells": [{str: __GRAMMAR_VERSION}],
            Optional("constraints"): __str_or_list,
            Optional("floorplan"): str,
            Optional("map"): str,
            Optional("tech"): str,
            Optional("wireload"): {
                "name": str,
                "library": str,
            },
            Optional("ips"): [{str: __GRAMMAR_VERSION}],
            "modes": [
                {
                    "name": str,
                    "corner": str,
                    Optional("usage"): [__mode_usage_config],
                    Optional("constraints"): str,
                    Optional("tluplus"): str,
                    Optional("spef"): str,
                    Optional("rc_corner"): str,
                }
            ],
        },
    }
)

ALLOWED_DESIGN_OBJ_TYPES = ["std_cells", "ips"]

##################################################################################################
#
# Power Analysis config file grammar
#
###################################################################################################

GRAMMAR_PWR_CONFIG = GrammarSchema(
    {
        "strip_path": str,
        "scenarios": [
            {
                "name": str,
                "mode": str,
                "simulation_target": str,
                "test_name": str,
                "from": int,
                "to": int,
                Optional("randomized"): bool,
            }
        ],
    }
)

##################################################################################################
#
# Memory map generator file grammar
#
###################################################################################################


class GRAMMAR_MEM_MAP_CONFIG:

    schema = GrammarSchema(
        {
            "name": str,
            Optional("short_name", default=""): str,
            "start_addr": int,
            "end_addr": int,
            Optional("reg_map"): str,
            Optional("regions"): Or(list, str),
        }
    )

    @classmethod
    def validate(cls, value: dict):
        if value["start_addr"] < 0:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"Region: {value['name']} has a negative start address defined ({hex(value['start_addr'])})",
            )

        if value["end_addr"] < 0:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"Region: {value['name']} has a negative end address defined ({hex(value['end_addr'])})",
            )

        if value["start_addr"] == value["end_addr"]:
            ts_print(
                f"WARNING: Region: {value['name']} has the same start and end addresses: {hex(value['start_addr'])}",
                color=TsColors.RED,
            )

        elif value["start_addr"] > value["end_addr"]:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"Region: {value['name']} has start address ({hex(value['start_addr'])}) greater than end address ({hex(value['end_addr'])})",
            )

        if "regions" in value and "reg_map" in value:
            ts_throw_error(TsErrCode.ERR_MMAP_0, value["name"])

        cls.schema.validate(value)
