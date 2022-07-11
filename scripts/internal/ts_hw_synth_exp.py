# -*- coding: utf-8 -*-

####################################################################################################
# Synthesis tool export
#
# TODO: License
####################################################################################################

from .ts_hw_global_vars import *
from .ts_hw_logging import *
from .ts_hw_common import *


def __get_header(tool: str) -> list:
    """
    Export header
    """
    lines = []
    lines.append("#####################################################################################")
    lines.append(f"# {tool} synthesis source script")
    lines.append("#")
    lines.append("# This script is exported by ts-hw-scripts and it shall be sourced by dc_shell to load")
    lines.append(f"# RTL source files from target '{TsGlobals.TS_SIM_CFG['target']}' to dc_shell.")
    lines.append("#")
    if tool == "dc_shell":
        lines.append(f"# Sourcing this file requires TS_SYNTH_DIR to be set..")
    elif tool == "vivado":
        lines.append("# Sourcing this file sets variable TS_VIVADO_DEFINES and TS_VIVADO_INCDIRS which gather")
        lines.append("# Verilog defines and include directories. These variables shall be used with 'synth_design'")
        lines.append("# command.")
    else:
        raise NotImplementedError(f"Tool '{tool}' not supported")
    lines.append("#")
    lines.append("# THIS FILE IS AUTO-GENERATED. DO NOT MODIFY IT!")
    lines.append("#")
    lines.append("#####################################################################################")
    lines.append("")

    return lines


def __write_file(lines: list, tcl_file: str, tool: str):
    """
    Export TCL file
    """
    with open(ts_get_curr_dir_rel_path(tcl_file), "w") as f:
        __add_newline = lambda x: x + '\n'
        # write header
        f.writelines(map(__add_newline, __get_header(tool)))
        # write body
        f.writelines(map(__add_newline, lines))


def export_dc_tcl(tcl_file: str):
    """
    Export DC TCL file.
    :param tcl_file: Path to TCL file relative to directory where scripts are called.
    """

    def __get_defines(element):
        return set(element.get("define", {}).items())

    def __get_included_dirs(element):
        return set(map(ts_get_root_rel_path, element.get("include_dirs", [])))

    lines = []

    # Create design libraries and folders for them
    lines.append("# Defining design libraries")
    for lib in TsGlobals.TS_SIM_SRCS_BY_LIB:
        lines.append(f"exec mkdir -p $TS_SYNTH_DIR/{lib}")
        lines.append(f"define_design_lib {lib} -path $TS_SYNTH_DIR/{lib}\n")

    # Export files
    for lib, source_files in TsGlobals.TS_SIM_SRCS_BY_LIB.items():
        lines.append("#############################################################")
        lines.append(f"# '{lib}' library")
        lines.append("#############################################################\n")

        for source_file in source_files:
            lang = source_file.get("lang")
            if lang is None:
                _, ext = os.path.splitext(source_file["full_path"])
                try:
                    lang = {
                        ".vhd": "vhdl",
                        ".v": "verilog",
                        ".sv": "sverilog",
                        ".svp": "sverilog"
                    }[ext]
                except KeyError:
                    ts_throw_error(TsErrCode.GENERIC,
                                    f"{source_file['full_path']}: extension '{ext}' not supported!")
            else:
                try:
                    lang = {
                        "vhdl": "vhdl",
                        "verilog": "verilog",
                        "system_verilog": "sverilog"
                    }[lang]
                except KeyError:
                    ts_throw_error(TsErrCode.GENERIC,
                                    f"{source_file['full_path']}: language '{lang}' unknown!")

            file_cmd = [f"analyze -format {lang} \\\n"]

            file_cmd.append(f"-work {lib} \\\n")

            # defines and include_dirs (only Verilog and SystemVerilog)
            if lang != "vhdl":
                defines = set()
                # sim cfg file defines
                defines.update(__get_defines(TsGlobals.TS_SIM_CFG))
                # target specific defines
                defines.update(__get_defines(TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_SIM_CFG["target"]]))
                # src list file defines
                defines.update(__get_defines(source_file))
                defines = [f"{name}={val}" if val is not None else name for name, val in defines]
                if defines:
                    file_cmd.append(f"-define {{{' '.join(defines)}}} \\\n")

                included_dirs = set()
                # sim cfg file include_dirs
                included_dirs.update(__get_included_dirs(TsGlobals.TS_SIM_CFG))
                # target specific include_dirs
                included_dirs.update(__get_included_dirs(TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_SIM_CFG["target"]]))
                # src list file include_dirs
                included_dirs.update(__get_included_dirs(source_file))
                if included_dirs:
                    file_cmd.append(f"-vcs +incdir+{'+'.join(included_dirs)} \\\n")

            file_cmd.append(f"{source_file['full_path']}\n\n")

            lines.append("\t\t\t\t".join(file_cmd))

    # Elaborate the top entity
    lines.append(f"# Elaborate top entity of '{TsGlobals.TS_SIM_CFG['target']}' target")
    try:
        hdl_lib, top_entity = TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_SIM_CFG["target"]]["top_entity"].split(".")
        lines.append(f"elaborate -work {hdl_lib} {top_entity}\n")
    except ValueError:
        lines.append(f"elaborate {TsGlobals.TS_SIM_CFG['targets'][TsGlobals.TS_SIM_CFG['target']]['top_entity']}\n")

    __write_file(lines, tcl_file, "dc_shell")


def export_vivado_tcl(tcl_file: str):
    """
    Export Vivado TCL file.
    :param tcl_file: Path to TCL file relative to directory where scripts are called.
    """

    _ALREADY_DEFINED = set()
    def __add_define(lst, define):
        if define in _ALREADY_DEFINED:
            return
        _ALREADY_DEFINED.add(define)
        define_name, define_val = define
        if define_val is not None:
            lst.append(f'append TS_VIVADO_DEFINES "{define_name}={define_val} "\n')
        else:
            lst.append(f'append TS_VIVADO_DEFINES "{define_name} "\n')

    _ALREADY_INCLUDED_DIRS = set()
    def __add_included_dir(lst, include_dir):
        if include_dir in _ALREADY_INCLUDED_DIRS:
            return
        _ALREADY_INCLUDED_DIRS.add(include_dir)
        lst.append(f'append TS_VIVADO_INC_DIRS "{ts_get_root_rel_path(include_dir)} "\n')

    def _add_define_and_include_dirs(element):
        acc = []
        for define in element.get("define", {}).items():
            __add_define(acc, define)
        for include_dir in element.get("include_dirs", {}):
            __add_included_dir(acc, include_dir)
        if acc:
            return "".join(acc) + "\n"
        return ""

    lines = []

    # Write empty variables
    lines.append('set TS_VIVADO_DEFINES ""')
    lines.append('set TS_VIVADO_INC_DIRS ""\n')

    # sim cfg file defines and include_dirs
    lines.append(_add_define_and_include_dirs(TsGlobals.TS_SIM_CFG))

    # target specific file defines and include_dirs
    lines.append(_add_define_and_include_dirs(TsGlobals.TS_SIM_CFG["targets"][TsGlobals.TS_SIM_CFG["target"]]))

    # Export files
    for lib, source_files in TsGlobals.TS_SIM_SRCS_BY_LIB.items():
        lines.append("#############################################################")
        lines.append(f"# '{lib}' library")
        lines.append("#############################################################\n")

        for source_file in source_files:
            lang = source_file.get("lang")
            if lang is None:
                _, ext = os.path.splitext(source_file["full_path"])
                try:
                    cmd = {
                        ".vhd": "read_vhdl",
                        ".v": "read_verilog",
                        ".sv": "read_verilog -sv",
                        ".svp": "read_verilog -sv"
                    }[ext]
                except KeyError:
                    ts_throw_error(TsErrCode.GENERIC,
                                    f"{source_file['full_path']}: extension '{ext}' not supported!")
            else:
                try:
                    cmd = {
                        "vhdl": "read_vhdl",
                        "verilog": "read_verilog",
                        "system_verilog": "read_verilog -sv"
                    }[lang]
                except KeyError:
                    ts_throw_error(TsErrCode.GENERIC,
                                    f"{source_file['full_path']}: language '{lang}' unknown!")

            # write file synthesis command
            lines.append(f"{cmd} -library {lib} \\\n\t\t\t\t{source_file['full_path']}\n")

            # src list file defines and include_dirs (only Verilog and SystemVerilog)
            if lang != "vhdl":
                lines.append(_add_define_and_include_dirs(source_file))

    __write_file(lines, tcl_file, "vivado")

