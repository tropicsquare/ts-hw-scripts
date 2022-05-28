# -*- coding: utf-8 -*-

####################################################################################################
# Simulator/Compiler interface for Tropic Square simulation scripting system.
#
# TODO: License
####################################################################################################

import os
import random
import shutil
import time
import datetime
import contextlib

from .ts_hw_common import *
from .ts_hw_test_list_files import *


__SIMULATOR_COMMANDS = {
    "vcs": {
        # Common options for all steps of a flow!
        "common_options": "-full64 -nc",
        "compile": {
            # Common options only for compile step
            "common_options": "",
            "languages": {
                "vhdl": "vhdlan",
                "verilog": "vlogan -incr_vlogan +lint=all,noNS +warn=all,noLCA_FEATURES_ENABLED",
                "system_verilog": "vlogan -incr_vlogan -sverilog +lint=all,noNS +warn=all,noLCA_FEATURES_ENABLED -assert svaext"
            },
            "vhdl_std": {
                "vhdl87": "-vhdl87",
                "vhdl93": "",
                "vhdl02": "-vhdl02",
                "vhdl08": "-vhdl08"
            },
            "verilog_std": {
                "v95": "-v95",
                "v01": "",
                "v05": "-v2005"
            },
            "library": "-work {}",
            "define": "+define+{}",
            "define_val": "+define+{}={}",
            "coverage": "",
            "compile_debug": "",
            "verbose": "-verbose",
            "log_file": "-l {}",
            "include_dirs": "+incdir+{}",
            "enable_uvm":"-ntb_opts uvm"
        },
        "elaborate": {
            "command": "vcs +plusarg_save",
            "common_options": "-lca -notice -psl +warn=all,noLCA_FEATURES_ENABLED +lint=TFIPC-L +lint=PCWM",
            "compile_debug": "-debug_access+all",

            # This overrides rules for searching finest Verilog resolution or default VHDL resolution
            "simulation_resolution": "-sim_res=1{}",

            # To run in GUI mode, debug access must be set! We don't leave it to user to set it, but
            # we set it automatically if user wants to go to GUI! The same goes for "dump_waves"
            "gui": "-debug_access+all -debug_region+cell",
            "dump_waves": "-debug_access+all -debug_region+cell",
            "coverage": "-cm line+cond+fsm+tgl+branch+assert",
            "verbose": "-v",
            "license_wait": "-licqueue",
            "log_file": "-l {}",
            "seed": "+ntb_random_seed={}",
            "enable_uvm":"$VCS_HOME/etc/uvm/dpi/uvm_dpi.cc"
        },
        "simulate": {
            "binary": "simv",
            "common_options": "-ucli",
            "sim_cmd_file": "-do {}",
            "log_file": "-l {}",
            "seed": "",
            "exitstatus": "-exitstatus",
            "license_wait": "-licqueue",
            "uvm_test_name": "+UVM_TESTNAME={}"
        }
    }
}

__ALLOWED_FILE_EXTENSIONS = {
    ".vhd": "vhdl",
    ".v": "verilog",
    ".sv": "system_verilog",
    ".svh": "system_verilog",
    ".svi": "system_verilog",
    ".svp": "system_verilog"
}

__SIM_CONFIG_FILES = {
    "vcs": "synopsys_sim.setup"
}

__GUI_COMPILE_OPTIONS = {
    None: {
        "languages": {
            "vhdl": "-psl -assert psl_in_block",
            "verilog": "",
            "system_verilog": ""
        }
    },
    "dve": {
        "languages": {
            "vhdl": "-psl -assert psl_in_block",
            "verilog": "",
            "system_verilog": ""
        }
    },
    "verdi": {
        "languages": {
            "vhdl": "-kdb",
            "verilog": "-kdb -lca",
            "system_verilog": "-kdb -lca"
        }
    }
}

def __get_gui_simulation_options() -> list:
    gui_opts = []

    gui = ts_get_cfg("gui")
    if gui is not None:
        assert gui in ("dve", "verdi"), f"{gui} not supported!"

        gui_opts.append(f"-gui={gui}")

        session_file = ts_get_cfg().get("session_file")
        if session_file is not None:
            session_file = ts_get_root_rel_path(session_file)

            if gui == "dve":
                gui_opts.append(f"-dve_opt -session={session_file}")
            elif gui == "verdi":
                gui_opts.append(f'-verdi_opts "-sx -ssr {session_file}"')
        else:
            if gui == "verdi":
                gui_opts.append('-verdi_opts "-sx"')
    return gui_opts


def __generate_sim_config_file():
    """
    Generates simulator specific config file (if needed).
    """
    simulator = ts_get_cfg("simulator")

    if simulator == "vcs":
        # Generates .synopsys_sim.setup
        lines = []

        # Add variables which change simulation behavior
        lines.append("-- Simulation settings:")
        lines.append(f"ASSERT_STOP = {ts_get_cfg('stop_severity')}")
        lines.append("VPDDELTACAPTURE = ON")

        # Only set XLRM_TIME when we override the simulation resolution from command line!
        if "simulation_resolution" in ts_get_cfg():
            lines.append("XLRM_TIME=TRUE")
        lines.append("")

        lines.append("-- Default library mapping:")
        lines.append("WORK > DEFAULT")
        lines.append(f"DEFAULT: {ts_get_cfg('build_dir')}")
        lines.append("")

        lines.append("-- Library mapping:")
        for lib, lib_files in TsGlobals.TS_SIM_SRCS_BY_LIB.items():
            lines.append(f"{lib.upper()} : {os.path.join(ts_get_cfg('build_dir'), lib)}")

        if ts_is_uvm_enabled():
            lines.append(f"UVM : {os.path.join(ts_get_cfg('build_dir'), 'uvm')}")

        # TODO: Allow passing configuration from YAML config file to the synopsis_sym_setup
        #       Some sort of append is needed here

        with open(os.path.join(os.getcwd(), __SIM_CONFIG_FILES[simulator]), "w") as f:
            f.writelines(map(lambda x: x + '\n', lines))

    else:
        ts_script_bug(f"Simulator '{simulator}' not supported in function '__generate_sim_config_file'")


def __add_comp_sim_elab_opts(cfg_dict: dict, kwd: str) -> list:
    """
    Adds comp_options, elab_options or sim_options to compiler/elaborator/simulator command
    :param cfg_dict: Dictionary with "elab_options", "comp_options" or "sim_options" values.
    :param kwd: Keyword to choose from the dictionary.
    """
    # Do not add anything if desired keyword is not part of dictionary or dictionary is not defined!
    try:
        cfg_dict[kwd]
    except (TypeError, KeyError):
        return []

    opts = []
    for item in ("common", ts_get_cfg("simulator")):
        value = cfg_dict[kwd].get(item)
        if value is not None:
            opts.append(value)
    return opts


def __add_generics(cfg_dict: dict) -> list:
    """
    Adds generics (VHDL) to elaboration command line.
    :param cfg_dict: Dictionary with generics configuration
    :param gfile: Name of generics file
    :param test_binary_dir: Path to directory with binary for current directory.
    """
    try:
        cfg_dict["generics"]
    except (TypeError, KeyError):
        return []

    cmd = []

    simulator = ts_get_cfg("simulator")

    if simulator == "vcs":
        
        for gen_name, gen_val in cfg_dict["generics"].items():

            str_val = str(gen_val)

            # Wrap with correct appostrophes
            if str_val.startswith("'"):
                gen_val = '"' + str_val + '"'
            elif str_val.startswith('"'):
                gen_val = "'" + str_val + "'"
            # Time type is special...
            elif re.match("[0-9]+(fs|ps|ns|us|ms|s)", str_val):
                gen_val = "'" + str_val + "'"
            # Simple strings without any quotes
            elif isinstance(gen_val, str):
                gen_val = "'\"{}\"'".format(gen_val)

            cmd.append(f"-gvalue {gen_name}={gen_val}")

    else:
        ts_script_bug(f"Simulator '{simulator}' not supported in function '__add_generics'")

    return cmd


def __add_parameters(cfg_dict: dict) -> list:
    """
    Add parameters (Verilog) to elaboration command line.
    :param cfg_dict: Dictionary with generics configuration
    """
    try:
        cfg_dict["parameters"]
    except (TypeError, KeyError):
        return []

    cmd = []

    simulator = ts_get_cfg("simulator")

    if simulator == "vcs":

        for param_name, param_val in cfg_dict["parameters"].items():

            if isinstance(param_val, str):
                param_val = r"'\"" + param_val.replace(r" ", r"\ ") + r"\"'"
            cmd.append(f"-pvalue+{param_name}={param_val}")

    else:
        ts_script_bug(f"Simulator '{simulator}' not supported in function '__add_parameters'")

    return cmd


def __build_compile_command(language: str, sim_cmds_dict: dict,
                            source_file_dict: dict, log_file_path: str) -> str:
    """
    Builds compile command.
    :param language: Language of source file
    :param sim_cmds_dict: Simulator specific dictionary
    :param source_file_dict: Source file dictionary (entry of "source_list" list)
    :param log_file_path: Path to compile log file
    """
    def __add_define(config_dict, comp_cmds_dict):
        try:
            config_dict["define"]
        except (TypeError, KeyError):
            return []

        return [comp_cmds_dict["define"].format(k)
                if v is None
                else comp_cmds_dict["define_val"].format(k, v)
                for k, v in config_dict["define"].items()]

    def __add_include_dirs(config_dict, comp_cmds_dict):
        try:
            config_dict["include_dirs"]
        except (TypeError, KeyError):
            return []

        # We can afford to expand relative to TS_REPO_ROOT because all include directories
        # relative to source list files were expanded upon list file load!
        return [comp_cmds_dict["include_dirs"].format(ts_get_root_rel_path(inc_dir))
                for inc_dir in config_dict["include_dirs"]]


    comp_cmds_dict = sim_cmds_dict["compile"]

    # Get compile command
    try:
        comp_cmd = [comp_cmds_dict["languages"][language]]
        comp_cmd.append(__GUI_COMPILE_OPTIONS[ts_get_cfg("gui")]["languages"][language])
    except KeyError:
        # Language not supported
        ts_throw_error(TsErrCode.ERR_CMP_1, language, ts_get_cfg("simulator"), 
            list(comp_cmds_dict["languages"].keys()))

    # Check compile command can be found
    comp_cmd_short, *_ = comp_cmd[0].split(maxsplit=1)
    if not shutil.which(comp_cmd_short):
        ts_throw_error(TsErrCode.ERR_CMP_3, comp_cmd_short, ts_get_cfg("simulator"))

    # Add work library
    comp_cmd.append(comp_cmds_dict["library"].format(source_file_dict["library"]))

    # Macro definitions and include files are verilog only!
    if language in ("verilog", "system_verilog"):
        # Add Global, target-specific and file-specific defines and include directories
        for function in (__add_define, __add_include_dirs):
            for cfg_dict in (ts_get_cfg(),
                            ts_get_cfg("targets")[ts_get_cfg("target")],
                            source_file_dict):
                comp_cmd.extend(function(cfg_dict, comp_cmds_dict))

    # VHDL language standard
    if language == "vhdl":
        comp_cmd.append(comp_cmds_dict["vhdl_std"][ts_get_cfg("vhdl_std")])
    # Verilog language standard
    elif language == "verilog":
        comp_cmd.append(comp_cmds_dict["verilog_std"][ts_get_cfg("verilog_std")])

    # Add all step specific options and compile specific option
    comp_cmd.append(sim_cmds_dict["common_options"])
    comp_cmd.append(comp_cmds_dict["common_options"])

    # Add coverage specific argument
    if TsGlobals.TS_SIM_CFG["coverage"]:
        comp_cmd.append(comp_cmds_dict["coverage"])

    # Add Debug specific argument
    if TsGlobals.TS_SIM_CFG["compile_debug"]:
        comp_cmd.append(comp_cmds_dict["compile_debug"])

    # Add log file
    comp_cmd.append(comp_cmds_dict["log_file"].format(log_file_path))

    # Add verbose options
    if ts_is_very_verbose():
        comp_cmd.append(comp_cmds_dict["verbose"])

    # Add Global, Target specific and file specific compile options
    for cfg_dict in (ts_get_cfg(),
                        ts_get_cfg("targets")[ts_get_cfg("target")],
                        source_file_dict):
        comp_cmd.extend(__add_comp_sim_elab_opts(cfg_dict, "comp_options"))

    # Add Extra compile options from command line
    comp_cmd.append(ts_get_cfg("add_comp_options"))

    # Add Language specific compile options from command line
    if language == "vhdl":
        comp_cmd.append(ts_get_cfg("add_vhdl_comp_options"))
    elif language == "verilog":
        comp_cmd.append(ts_get_cfg("add_verilog_comp_options"))
    elif language == "system_verilog":
        comp_cmd.append(ts_get_cfg("add_verilog_comp_options"))
        # Append UVM option if enabled by globally or per target!
        if ts_is_uvm_enabled():
            comp_cmd.append(comp_cmds_dict["enable_uvm"])

    return " ".join(filter(str.strip, comp_cmd))


def __run_uvm_compile() -> int:
    """
    Runs UVM for compilation.
    """
    ts_info(TsInfoCode.INFO_GENERIC, "Enabling UVM...")

    simulator = ts_get_cfg("simulator")

    if simulator == "vcs":
        # VCS needs one call of vlogan with no file path provided to enable UVM
        # compilation. To do this, we build a "dummy file" dictionary and place
        # the compilation into UVM library!
        dummy_src_file = {
            "library": "uvm",
            "full_path": ""
        }

        tmp_log_file_path = ts_get_root_rel_path(TsGlobals.TS_TMP_LOG_FILE_PATH)

        cmd = __build_compile_command("system_verilog",
                                    __SIMULATOR_COMMANDS[ts_get_cfg("simulator")],
                                    dummy_src_file, tmp_log_file_path)

        ts_info(TsInfoCode.INFO_GENERIC, "UVM compile command:")
        ts_info(TsInfoCode.INFO_GENERIC, cmd)

    else:
        ts_script_bug(f"Simulator '{simulator}' not supported in function '__run_uvm_compile'")

    return exec_cmd_in_dir(ts_get_cfg("build_dir"), cmd)


def __run_compile_command(comp_cmd, comp_file_list, log_file_path):
    """
    Runs compile command
    """
    log_files_merged = "\n    ".join(comp_file_list)
    # Print the command
    ts_info(TsInfoCode.INFO_CMN_26, "\n    " + log_files_merged)
    ts_info(TsInfoCode.INFO_GENERIC, comp_cmd)

    # Finally, call the compile command and evaluate it
    # Stash stderr. Error message is anyway printed to stdout too.
    comp_res = exec_cmd_in_dir(ts_get_cfg("build_dir"), comp_cmd, no_std_err=True)

    # Append temporary log file to global log file
    with open(log_file_path, "a") as log_file, open(log_file_path, "r") as tmp_log_file:
        shutil.copyfileobj(tmp_log_file, log_file)

    # Check compilation result
    if comp_res != 0:
        ts_throw_error(TsErrCode.ERR_CMP_2, comp_res)


def __compile_all_files():
    """
    Compiles all source files. If compilation of any file fails, throws an exception.
    """

    def _get_included_files(*elements):
        included_dirs = set()
        for element in elements:
            with contextlib.suppress(KeyError):
                included_dirs.update(set(ts_get_root_rel_path(d) for d in element["include_dirs"]))

        included_files = []
        for d in included_dirs:
            for f in os.scandir(d):
                if os.path.splitext(f)[1] in (".v", ".sv", ".svh", ".svi", ".pkg") \
                and os.path.isfile(f) and not os.path.islink(f):
                    included_files.append(os.path.join(d, f))
        return included_files

    sim_cmds_dict = __SIMULATOR_COMMANDS[ts_get_cfg("simulator")]

    # Compilation log file
    log_file_name = "compile_{}_{}.log".format(ts_get_cfg("target"), 
                                                datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
    log_file_path = ts_get_root_rel_path(os.path.join(TsGlobals.TS_COMP_LOG_DIR_PATH,
                                                      log_file_name))
    # Temporary log file
    tmp_log_file_path = ts_get_root_rel_path(TsGlobals.TS_TMP_LOG_FILE_PATH)

    # Get included files (relevant for Verilog and SystemVerilog)
    included_files = _get_included_files(TsGlobals.TS_SIM_CFG, TsGlobals.TS_SIM_CFG["targets"][ts_get_cfg("target")])

    # Now we compile files sequentially one by one. This is because we allow to pass file
    # specific arguments, defines! If there is performance problem at some point, we might
    # optimize this!
    for lib, source_files in TsGlobals.TS_SIM_SRCS_BY_LIB.items():
        ts_print(f"Compiling files for library: '{lib}'", color=TsColors.PURPLE)

        # Create sub-directory for library if it does not exist
        with contextlib.suppress(FileExistsError):
            lib_dir = os.path.join(ts_get_cfg("build_dir"), lib)
            os.mkdir(lib_dir)
            ts_debug(f"Creating directory: {lib_dir}")

        # Maintain a list of the files which have already been compiled
        # so we can skip them if they have not changed
        lib_list_of_files = os.path.join(lib_dir, "files.lst")
        try:
            with open(lib_list_of_files, "r") as f:
                already_compiled_files = set(f.read().splitlines())
            lib_last_modification_time = os.path.getmtime(lib_list_of_files)
        except FileNotFoundError:
            already_compiled_files = set()
            lib_last_modification_time = 0.0

        # If any globally included file is newer than last compilation
        # force compilation (Verilog and SystemVerilog)
        force_verilog = any(os.path.getmtime(f) > lib_last_modification_time for f in included_files)

        # Called compile command
        final_comp_cmd = ""
        final_comp_file_lst = ""

        # Compile files one by one
        for source_file_dict in source_files:
            ts_debug(f"Attempting to compile file: {source_file_dict['full_path']}")
            skip_file = False

            # Check if simulator supports the language
            language = source_file_dict.get("lang")
            if language is None:
                _, file_ext = os.path.splitext(source_file_dict["file"])
                try:
                    language = __ALLOWED_FILE_EXTENSIONS[file_ext]
                except KeyError:
                    ts_throw_error(TsErrCode.ERR_CMP_0, file_ext, source_file_dict["full_path"],
                                   list(__ALLOWED_FILE_EXTENSIONS.keys()))
            elif language not in __ALLOWED_FILE_EXTENSIONS.values():
                ts_throw_error(TsErrCode.ERR_CMP_1, language, ts_get_cfg("simulator"),
                                list(__ALLOWED_FILE_EXTENSIONS.values()))

            # If file is not in the list, compile it
            if source_file_dict["full_path"] in already_compiled_files:
                # Do not compile file if it has not changed since last compilation of the lib
                # or if any of its includes has changed (only Verilog and SystemVerilog)
                if os.path.getmtime(source_file_dict["full_path"]) < lib_last_modification_time:
                    if language == "vhdl" \
                        or (not force_verilog
                            and all(map(lambda f: os.path.getmtime(f) < lib_last_modification_time,
                                    _get_included_files(source_file_dict)))):
                            ts_info(TsInfoCode.INFO_GENERIC, f"Skipping unchanged file {source_file_dict['full_path']}")
                            skip_file = True

            # Build compile command (without file specified)
            local_comp_cmd = __build_compile_command(language, sim_cmds_dict, source_file_dict, tmp_log_file_path)

            # Set first compile command
            if final_comp_cmd == "":
                final_comp_cmd = local_comp_cmd
                final_comp_file_lst = []

            # If we detected different compile command for currently search file,
            # compile files accumulated in the list so far
            if (local_comp_cmd != final_comp_cmd):
                final_comp_cmd += " " + " ".join(final_comp_file_lst)

                if (len(final_comp_file_lst) > 0):
                    __run_compile_command(final_comp_cmd, final_comp_file_lst, tmp_log_file_path)

                # Replace the compile command with new one
                final_comp_cmd = local_comp_cmd
                final_comp_file_lst = []
                
            # Append file to be compiled to list of compiled files
            if not skip_file:
                final_comp_file_lst.append(source_file_dict["full_path"])

            # On last file, we always need to compile
            if (source_file_dict == source_files[-1]):
                if (len(final_comp_file_lst) > 0):
                    final_comp_cmd += " " + " ".join(final_comp_file_lst)
                    __run_compile_command(final_comp_cmd, final_comp_file_lst, tmp_log_file_path)

            # update list of files already compiled
            with open(lib_list_of_files, "a") as f:
                f.write(source_file_dict["full_path"] + "\n")

        # Update file timestamp
        os.utime(lib_list_of_files)

    # Remove temporary file
    with contextlib.suppress(FileNotFoundError):
        os.remove(tmp_log_file_path)


def __write_log_trailer(log_file_path, exit_code, run_time, log_type):
    """
    Appends additional simulation/elaboration information to simulation (simulator exit code, run time) log
    file.
    :param log_file_path: Path to a log file
    :param sim_exit_code: Simulator exit code
    :param run_time: Simulation run time (in seconds).
    :param log_type: ELAB (elaboration log) or SIM (sim log)
    """
    # Append additional information to simulation log-file
    with open(log_file_path, "a") as log_file:
        log_file.write("\n")
        log_file.write("TS_{}_RUN_EXIT_CODE: {}\n".format(log_type, exit_code))
        log_file.write("TS_{}_RUN_TIME: {}\n".format(log_type, run_time))
        

def __build_elab_command(test: dict, top_entity: str, log_file_path: str,
                            test_binary_dir: str) -> str:
    """
    Builds elaboration command.
    :param test: Test object/dictionary (from test list file)
    :param top_entity: Top design entity to be elaborated.
    :param test_binary_dir: Directory in which test binary will be stored.
    """
    cmds = __SIMULATOR_COMMANDS[ts_get_cfg("simulator")]
    elab_dict = cmds["elaborate"]

    elab_cmd = [elab_dict["command"]]

    if ts_get_cfg("coverage"):
        elab_cmd.append(elab_dict["coverage"])

    if ts_get_cfg("compile_debug"):
        elab_cmd.append(elab_dict["compile_debug"])

    # Add common options
    elab_cmd.append(cmds["common_options"])

    # Add GUI and dump waves options
    if ts_get_cfg("gui") is not None:
        elab_cmd.append(elab_dict["gui"])
    if ts_get_cfg("dump_waves"):
        elab_cmd.append(elab_dict["dump_waves"])

    # Add simulation seed
    if elab_dict.get("seed"):
        elab_cmd.append(elab_dict["seed"].format(test["seed"]))

    # Add verbosity options
    if ts_is_very_verbose():
        elab_cmd.append(elab_dict["verbose"])

    # Add license wait option
    if ts_get_cfg("license_wait"):
        elab_cmd.append(elab_dict["license_wait"])

    # Add common options
    elab_cmd.append(elab_dict["common_options"])

    # Add Global, Target specific, Test specific and Verbosity level specifi elab. options
    for cfg_dict in (ts_get_cfg(),
                        ts_get_cfg("targets")[ts_get_cfg("target")],
                        get_test(test["name"], TsGlobals.TS_TEST_LIST),
                        ts_get_cfg("sim_verbosity_levels")[ts_get_cfg("sim_verbosity")]):
        elab_cmd.extend(__add_comp_sim_elab_opts(cfg_dict, "elab_options"))

    # Add extra options passed from command line
    elab_cmd.append(ts_get_cfg("add_elab_options"))

    # Add Log file path
    elab_cmd.append(elab_dict["log_file"].format(log_file_path))

    # Add global, target, test  and verbosity level specific generics and parameters
    for function in (__add_generics, __add_parameters):
        for cfg_dict in (ts_get_cfg(),
                            ts_get_cfg("targets")[ts_get_cfg("target")],
                            test,
                            ts_get_cfg("sim_verbosity_levels")[ts_get_cfg("sim_verbosity")]):
            elab_cmd.extend(function(cfg_dict))

    # Add test name generic/parameter (if set)
    for single_dict in (ts_get_cfg(), ts_get_cfg("targets")[ts_get_cfg("target")]):
        if single_dict["test_name_strategy"] == "generic_parameter":
            
            if "test_name_generic" in single_dict:
                cfg_dict = {"generics" : {single_dict["test_name_generic"]: test["name"]}}
                elab_cmd.extend(__add_generics(cfg_dict))

            if "test_name_parameter" in ts_get_cfg():
                cfg_dict = {"parameters" : {single_dict["test_name_parameter"]: test["name"]}}
                elab_cmd.extend(__add_parameters(cfg_dict))

    # Add simulation resolution
    with contextlib.suppress(TypeError, KeyError):
        elab_cmd.append(elab_dict["simulation_resolution"].format(TsGlobals.TS_SIM_CFG["simulation_resolution"]))

    # Add UVM elab options
    if ts_is_uvm_enabled():
        elab_cmd.append(elab_dict["enable_uvm"])

    # Append top entity
    elab_cmd.append(top_entity)

    return " ".join(filter(str.strip, elab_cmd))


def ts_sim_compile():
    """
    Compiles sources found by current configuration.
    """
    ts_print("Compilation starting", color=TsColors.PURPLE, big=True)
    ts_debug("Creating compile directory...")
    os.makedirs(ts_get_cfg("build_dir"), exist_ok=True)

    ts_debug("Generate simulation configuration file in 'sim' folder")
    orig_dir = os.getcwd()
    os.chdir(ts_get_root_rel_path(ts_get_cfg("build_dir")))
    __generate_sim_config_file()
    os.chdir(orig_dir)

    ts_debug("Create 'comp_log' directory (if it does not exist)")
    if ts_get_cfg("clear_logs"):
        shutil.rmtree(ts_get_root_rel_path(TsGlobals.TS_COMP_LOG_DIR_PATH), ignore_errors=True)
    create_sim_sub_dir(TsGlobals.TS_COMP_LOG_DIR_PATH)

    if ts_is_uvm_enabled():
        __run_uvm_compile()

    __compile_all_files()
    ts_print("Compilation successful", color=TsColors.PURPLE, big=True)


def __get_elab_sim_config_file(test_binary_dir: str):
    """
    Moves simulation config file from 'sim' folder where it is created by ts_sim_compile.py to
    test specific folder. This needs to be done because test will be launched in test specific
    folder!
    """
    ts_debug("Copy ts_sim_config from 'sim' to test binary directory")
    simulator = ts_get_cfg("simulator")
    sim_config_file_path = os.path.join(ts_get_cfg("build_dir"), __SIM_CONFIG_FILES[simulator])
    if not os.path.exists(sim_config_file_path):
        ts_throw_error(TsErrCode.ERR_ELB_3, sim_config_file_path)
    shutil.copy2(sim_config_file_path, test_binary_dir)

    if simulator == "vcs":
        ts_debug("Changing VCS ASSERT_STOP to be up-to date with config file!")
        file_path = os.path.join(test_binary_dir, __SIM_CONFIG_FILES[simulator])
        with open(file_path, "r") as fd:
            lines = fd.readlines()
        newlines = ["ASSERT_STOP = {}\n".format(ts_get_cfg("stop_severity")) 
                    if line.startswith("ASSERT_STOP") 
                    else line 
                    for line in lines]
        with open(file_path, "w") as fd_new:
            fd_new.writelines(newlines)


def ts_sim_elaborate(test: dict) -> str:
    """
    Elaborate the design for simulation
    :param test: Test dictionary object
    """
    ts_print("Running elaboration", color=TsColors.PURPLE, big=True)

    ts_debug("Check that compilation was executed before !")
    if not os.path.exists(ts_get_root_rel_path(TsGlobals.TS_SIM_BUILD_PATH)):
        ts_throw_error(TsErrCode.ERR_ELB_2)

    ts_debug("Get log file name")
    log_file_path = create_log_file_name(test["seed"], test["name"], "elab")

    ts_debug("Create test binary directory")
    test_binary_dir = ts_get_test_binary_dir(test)
    shutil.rmtree(test_binary_dir, ignore_errors=True)
    os.mkdir(test_binary_dir)

    __get_elab_sim_config_file(test_binary_dir)

    ts_debug("Get target's top entity")
    try:
        top_entity = ts_get_cfg("targets")[ts_get_cfg("target")]["top_entity"]
    except:
        ts_script_bug("Top entity shall be defined! No target without top entity shall be valid!")

    # Build elaboration command
    elab_cmd = __build_elab_command(test, top_entity, log_file_path, test_binary_dir)

    # Print elaboration command
    ts_info(TsInfoCode.INFO_GENERIC, elab_cmd)

    # Run elaboration in test specific directory
    run_time = time.time()
    elab_exit_code = exec_cmd_in_dir(test_binary_dir, elab_cmd,
                            ts_get_cfg("no_sim_out"), ts_get_cfg("no_sim_out"))
    run_time = time.time() - run_time

    # Append log trailer
    __write_log_trailer(log_file_path, elab_exit_code, run_time, "ELAB")

    # If elaboration fails it is very unlikely it will succeed in next tests, finish current script!
    if elab_exit_code != 0:
        ts_throw_error(TsErrCode.ERR_ELB_0, top_entity, elab_exit_code)

    ts_print("Elaboration successful", color=TsColors.PURPLE, big=True)

    return log_file_path


def __create_sim_command_file(test: str, user_specified_do_file: str) -> str:
    """
    Creates simulation specific command file ("do" file)
    :param test: Test dictionary object
    """
    simulator = ts_get_cfg("simulator")

    lines = []

    # If user specified do file exist, execute it before the generated one.
    if user_specified_do_file:
        fd = open(user_specified_do_file)
        lines.extend(fd.readlines())

    if simulator == "vcs":
        
        gui = ts_get_cfg("gui")

        # If wave dumping is enabled, instruct simulator to dump database
        if ts_get_cfg("dump_waves"):

            if gui == "verdi":
                type_db = "fsdb"
            else:
                type_db = "vpd"

            # In GUI mode, DVE opens the file automatically, no need to open the file
            if gui != "dve":
                db_path = os.path.join(ts_get_test_binary_dir(test), f"inter.{type_db}")
                lines.append(f"dump -file {db_path} -type {type_db.upper()}")
            lines.append("dump -enable")
            lines.append("dump -deltaCycle on")
            lines.append("dump -msv on")
            if gui == "verdi":
                lines.append("dump -add . -aggregates -fsdb_opt +all+sva")
                lines.append("dump -glitch on")
            else:
                lines.append("dump -add . -aggregates -fid VPD0")

        # If we open GUI, don't do "run", leave it up to user to run it interactively from GUI!
        if gui is None:
            lines.append("run")
            lines.append("dump -close")
            lines.append("exit")

        do_file_path = os.path.join(ts_get_test_binary_dir(test), "sim_cmd_file.do")
        with open(do_file_path, "w") as f:
            f.writelines(map(lambda x: x + '\n', lines))

        return do_file_path
    else:
        ts_script_bug(f"Simulator '{simulator}' not supported in function '__create_sim_command_file'")


def __build_sim_command(sim_binary: str, sim_cmds: dict, test: dict, log_file_path: str,
                        sim_cmd_file_path: str) -> str:
    """
    Builds simulation command.
    :param sim_binary: Simulator specific command to launch simulation
    :param sim_cmds: Simulator specific commands for various configurations.
    :param log_file_path: Absolute path to simulation log file
    :param sim_cmd_file_path: Path to simulator specific command file.
    """
    # Build simulation command line
    sim_cmd = [sim_binary]

    # Add simulation seed
    if sim_cmds.get("seed"):
        sim_cmd.append(sim_cmds["seed"].format(test["seed"]))

    # Add GUI options and session file
    sim_cmd.extend(__get_gui_simulation_options())

    # Add license wait option
    if ts_get_cfg("license_wait"):
        sim_cmd.append(sim_cmds["license_wait"])

    # Add Common options
    sim_cmd.append(sim_cmds["common_options"])

    # Add Global, Target specific and Test specific simulation options
    for cfg_dict in (ts_get_cfg(),
                        ts_get_cfg("targets")[ts_get_cfg("target")],
                        get_test(test["name"], TsGlobals.TS_TEST_LIST),
                        ts_get_cfg("sim_verbosity_levels")[ts_get_cfg("sim_verbosity")]):
        sim_cmd.extend(__add_comp_sim_elab_opts(cfg_dict, "sim_options"))

    # Add extra options passed from command line
    sim_cmd.append(ts_get_cfg("add_sim_options"))

    # Add log file path
    sim_cmd.append(sim_cmds["log_file"].format(log_file_path))

    # Add Sim exit command (sort-of VCS specific)
    sim_cmd.append(sim_cmds["exitstatus"])

    # Add simulator specific command file
    sim_cmd.append(sim_cmds["sim_cmd_file"].format(sim_cmd_file_path))

    # Add UVM test name if specified
    for single_dict in (ts_get_cfg(), ts_get_cfg("targets")[ts_get_cfg("target")]):
        if single_dict["test_name_strategy"] == "uvm":
            sim_cmd.append(sim_cmds["uvm_test_name"].format(test["name"]))

    return " ".join(filter(str.strip, sim_cmd))


def ts_sim_run(test: dict) -> str:
    """
    Launches simulation.
    :param test: Test object dictionary.
    """
    ts_print("Launching simulation", color=TsColors.PURPLE, big=True)

    # Check existence of simulation binary
    simulator = ts_get_cfg("simulator")
    sim_cmds = __SIMULATOR_COMMANDS[simulator]["simulate"]
    sim_binary = os.path.join(ts_get_test_binary_dir(test), sim_cmds["binary"])
    if not os.path.exists(sim_binary):
        ts_throw_error(TsErrCode.ERR_SIM_0, sim_binary)

    # Get test specific log file path
    log_file_path = create_log_file_name(test["seed"], test["name"], "sim")

    # Take do file if specified otherwise create it
    # Look for target-specific first and then global
    user_specified_do_file = None
    for sim_dict in (ts_get_cfg("targets")[ts_get_cfg("target")], ts_get_cfg()):
        user_specified_do_file = sim_dict.get("do_file")
        if user_specified_do_file is not None:
            break
    
    sim_cmd_file_path = __create_sim_command_file(test, user_specified_do_file)

    # Build simulation command line
    sim_cmd = __build_sim_command(sim_binary, sim_cmds, test, log_file_path, sim_cmd_file_path)

    ts_info(TsInfoCode.INFO_GENERIC, sim_cmd)

    # Run simulation
    run_time = time.time()
    sim_exit_code = exec_cmd_in_dir(ts_get_test_binary_dir(test), sim_cmd,
                                ts_get_cfg("no_sim_out"), ts_get_cfg("no_sim_out"))
    run_time = time.time() - run_time
    ts_print("Simulation Done", color=TsColors.PURPLE, big=True)

    ts_debug(f"Simulation exit code: {sim_exit_code}")

    # Append log trailer
    __write_log_trailer(log_file_path, sim_exit_code, run_time, "SIM")

    # Return path to log file for checking results!
    return log_file_path

