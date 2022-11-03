# -*- coding: utf-8 -*-

####################################################################################################
# Synthesis tool export
#
# TODO: License
####################################################################################################

from .ts_hw_global_vars import *
from .ts_hw_logging import *
from .ts_hw_common import *
from .ts_grammar import *


def __append_do_not_modify(lines: list):
    """
    Append Do not modify comment lines.
    """
    lines.append("#")
    lines.append("# THIS FILE IS AUTO-GENERATED. DO NOT MODIFY IT (UNLESS DOING LOCAL DEBUG)!")
    lines.append("#")


def __get_syn_rtl_header(tool: str) -> list:
    """
    Create export RTL synthesis header
    """
    lines = []
    lines.append("#####################################################################################")
    lines.append(f"# {tool} synthesis RTL source script")
    lines.append("#")
    lines.append(f'# This script is exported by ts-hw-scripts and it shall be sourced by {tool} to load')
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
    
    __append_do_not_modify(lines)
    
    lines.append("#####################################################################################")
    lines.append("")

    return lines


def __get_design_config_header(views: list, args) -> list:
    """
    Create export Design config file header
    """
    lines = []
    lines.append("#####################################################################################")
    lines.append("# Design configuration TCL script.")
    lines.append("#")
    lines.append("# This script is exported by ts-hw-scripts and it shall be sourced by a CAD tool to")
    lines.append("# load PDK views into TCL shell variables. Export is intentionally exporting view")
    lines.append("# paths to TCL variables only, not tool specific variables (e.g. 'link_library'). ")
    lines.append("#")
    lines.append("# This exported file contains following:")
    if args.add_top_entity:
        lines.append("#     - Design name (top entity)")
    if args.add_syn_rtl_build_dirs:
        lines.append("#     - RTL build directories for synthesis")
    for view in views:
        lines.append("#     - .{} view".format(view))

    __append_do_not_modify(lines)
    
    lines.append("#####################################################################################")
    lines.append("")

    return lines


def __write_syn_rtl_file(lines: list, tcl_file: str, tool: str):
    """
    Export TCL file
    """
    with open(ts_get_curr_dir_rel_path(tcl_file), "w") as f:
        __add_newline = lambda x: x + '\n'
        # write header
        f.writelines(map(__add_newline, __get_syn_rtl_header(tool)))
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
        lines.append(f'exec mkdir -p {TsGlobals.TS_SYN_BUILD_DIR}/{lib}')
        lines.append(f"define_design_lib {lib} -path {TsGlobals.TS_SYN_BUILD_DIR}/{lib}\n")

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

    __write_syn_rtl_file(lines, tcl_file, "dc_shell")


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

    __write_syn_rtl_file(lines, tcl_file, "vivado")


def __write_tcl_list(list_name: str, input_list: list, fd: str):
    """
    """
    # Filter for duplicities!
    filtered_input_list = []
    [filtered_input_list.append(x) for x in input_list if x not in filtered_input_list]
    fd.write("set {} [list \\\n".format(list_name))
    fd.writelines(filtered_input_list)
    fd.write("]\n\n")


def __write_tcl_dict(dict_name: str, input_dict: dict, fd: str):
    """
    """
    fd.write("set {} [dict create \\\n".format(dict_name))
    for key, val in input_dict.items():
        fd.write("    {} {} \\\n".format(key, val))
    fd.write("]\n\n".format(dict_name))


def __append_to_view_tcl_lists(view_list, folder_list, view_val):
    """
    """
    view_list_ext = []
    folder_list_ext = []

    if type(view_val) == list:
        for x in view_val:
            if os.path.isfile(x):
                view_list_ext = ["    {} \\\n".format(os.path.basename(x))]
                folder_list_ext = ["    {} \\\n".format(os.path.dirname(x))]
            else:
                folder_list_ext = ["    {} \\\n".format(x)]
    else:
        if os.path.isfile(view_val):
            view_list_ext = ["    {} \\\n".format(os.path.basename(view_val))]
            folder_list_ext = ["    {} \\\n".format(os.path.dirname(view_val))]
        else:
            folder_list_ext = ["    {} \\\n".format(view_val)]

    view_list.extend(view_list_ext)

    if folder_list_ext:
        folder_list.extend(folder_list_ext)


def __export_view_no_corners(view: str, fd):
    """
    """
     # Build lists for the views
    view_list = []
    folder_list = []

    for obj_type in ALLOWED_DESIGN_OBJ_TYPES:
        if obj_type in TsGlobals.TS_DESIGN_CFG["design"]:
            val = TsGlobals.TS_DESIGN_CFG["design"][obj_type]
            for target_obj in val:
                assert(type(target_obj) == dict)
                target_obj_name = list(target_obj.keys())[0]
                target_obj_version = list(target_obj.values())[0]
                obj = get_pdk_obj(obj_type, target_obj_name, target_obj_version)
                if view not in obj["views"]:
                    if ts_get_cfg("verbose") > 1:
                        ts_warning(TsWarnCode.WARN_PDK_3, target_obj_name, target_obj_version, view)
                    continue
                __append_to_view_tcl_lists(view_list, folder_list, obj["views"][view])
    if view_list:
        fd.write("# Views\n")
        __write_tcl_list("TS_{}_VIEWS".format(view.upper()), view_list, fd)
    if folder_list:
        fd.write("# Folders\n")
        __write_tcl_list("TS_{}_VIEW_DIRS".format(view.upper()), folder_list, fd)


def __export_view_with_corners(view: str, fd):
    """
    """
     # Build lists for the views
    view_dict = {}
    folder_list = []

    for obj_type in ALLOWED_DESIGN_OBJ_TYPES:
        if obj_type in TsGlobals.TS_DESIGN_CFG["design"]:
            val = TsGlobals.TS_DESIGN_CFG["design"][obj_type]
            for target_obj in val:
                assert(type(target_obj) == dict)
                target_obj_name = list(target_obj.keys())[0]
                target_obj_version = list(target_obj.values())[0]
                
                obj = get_pdk_obj(obj_type, target_obj_name, target_obj_version)
                if view not in obj["views"]:
                    ts_warning(TsWarnCode.WARN_PDK_3, target_obj_name, target_obj_version, view)
                    continue

                for mode in TsGlobals.TS_DESIGN_CFG["design"]["modes"]:
                    if mode["name"].upper() not in view_dict:
                        view_dict[mode["name"].upper()] = []
                    if mode["corner"] not in obj["views"][view]:
                        ts_warning(TsWarnCode.WARN_PDK_4, target_obj_name, target_obj_version, view, mode["corner"])
                        continue
                    __append_to_view_tcl_lists(view_dict[mode["name"].upper()], folder_list, obj["views"][view][mode["corner"]])

    # Write list per mode
    per_mode_dict = {}
    for mode_name, mode_views in view_dict.items():
        fd.write("# Mode '{}' views\n".format(mode_name))
        list_name = "TS_{}_{}_VIEWS".format(view.upper(), mode_name.upper())
        per_mode_dict[mode_name] = "${}".format(list_name)
        __write_tcl_list(list_name, mode_views, fd)
    
    # Write dictionary with all modes
    __write_tcl_dict("TS_{}_VIEWS".format(view.upper()), per_mode_dict, fd)  

    fd.write("# Folders\n")
    __write_tcl_list("TS_{}_VIEW_DIRS".format(view.upper()), folder_list, fd)


def __export_rtl_build_dirs(fd):
    """
    """
    build_dirs = []
    for lib in TsGlobals.TS_SIM_SRCS_BY_LIB.keys():
        build_dirs.append(f"    {TsGlobals.TS_SYN_BUILD_DIR}/{lib}\\\n")

    fd.write("#" * 85 + "\n")
    fd.write("# RTL build directories\n")
    fd.write("#" * 85 + "\n\n")

    __write_tcl_list("TS_{}_RTL_SYN_BUILD_DIRS".format(ts_get_design_top()), build_dirs, fd)


def __export_constraints(fd):
    """
    """
    fd.write("#" * 85 + "\n")
    fd.write("# Design constraints\n")
    fd.write("#" * 85 + "\n\n")

    # Global constraints
    if "constraints" in TsGlobals.TS_DESIGN_CFG["design"]:
        constr_list = []
        constrs = TsGlobals.TS_DESIGN_CFG["design"]["constraints"]
        if type(constrs) == str:
            constr_list.append("    {}\\\n".format(constrs))
        elif type(constrs) == list:
            for constr_file in constrs:
                constr_list.append("    {}\\\n".format(constr_file))
        fd.write("# Global constraints list\n")
        __write_tcl_list("TS_{}_GLOBAL_CONSTRAINTS".format(ts_get_design_top()), constr_list, fd)  

    # Per-mode constraints, joined to a global dictionary
    # If not defined, then not printed out
    constr_dict = {}
    for mode in TsGlobals.TS_DESIGN_CFG["design"]["modes"]:
        if "constraints" in mode:
            if not constr_dict:
                var = "TS_{}_{}_CONSTRAINTS {}\n".format(
                    ts_get_design_top().upper(), mode["name"].upper(), mode["constraints"])
                constr_dict[mode["name"].upper()] = mode["constraints"]
                fd.write("# Constraints for individual modes \n")
                fd.write("set {}".format(var))
            else:
                var = "TS_{}_{}_CONSTRAINTS {}\n".format(
                    ts_get_design_top().upper(), mode["name"].upper(), mode["constraints"])
                constr_dict[mode["name"].upper()] = mode["constraints"]
                fd.write("set {}".format(var))

    if constr_dict:
        fd.write("\n")
        __write_tcl_dict("TS_{}_CONSTRAINTS".format(ts_get_design_top()), constr_dict, fd)  

def __export_spef(fd):
    """

    """

    # Per-mode spef, joined to a global dictionary
    # If not defined, then not printed out
    constr_dict_part = {}
    constr_var_part  = f""

    for mode in TsGlobals.TS_DESIGN_CFG["design"]["modes"]:
        if "spef" in mode:
            if not constr_var_part:
                constr_var_part += f"{'#'*85}\n"
                constr_var_part += f"# SPEF files \n"
                constr_var_part += f"{'#'*85}\n\n"
                constr_var_part += f"# SPEF for individual modes \n\n"
            constr_var_part += f"set TS_{ts_get_design_top().upper()}_{mode['name'].upper()}_SPEF {mode['spef']}\n"
            constr_dict_part[mode["name"].upper()] = mode["spef"]

    fd.write(constr_var_part)

    if constr_dict_part != {}:
        fd.write("\n")
        __write_tcl_dict("TS_{}_SPEFS".format(ts_get_design_top()), constr_dict_part, fd)
    else:
        ts_warning(TsWarnCode.WARN_PDK_8)


def __export_tluplus(fd):
    """
    
    """

    # Per-mode tlu+, joined to a global dictionary
    # If not defined, then not printed out
    constr_dict_part = {}
    constr_var_part  = f""

    for mode in TsGlobals.TS_DESIGN_CFG["design"]["modes"]:
        if "tluplus" in mode:
            if not constr_var_part:
                constr_var_part += f"{'#'*85}\n"
                constr_var_part += f"# Tlu+ \n"
                constr_var_part += f"{'#'*85}\n\n"
                constr_var_part += f"# TLU+ for individual modes \n\n"
            constr_var_part += f"set TS_{ts_get_design_top().upper()}_{mode['name'].upper()}_TLU+ {mode['tluplus']}\n"
            constr_dict_part[mode["name"].upper()] = mode["tluplus"]

    fd.write(constr_var_part)

    if constr_dict_part != {}:
        fd.write("\n")
        __write_tcl_dict("TS_{}_TLU+".format(ts_get_design_top()), constr_dict_part, fd)
    else:
        ts_warning(TsWarnCode.WARN_PDK_9)


def __export_rc_corner(fd):
    """
    
    """
    constr_dict_part = {}
    constr_var_part  = f""

    for mode in TsGlobals.TS_DESIGN_CFG["design"]["modes"]:
        if "rc_corner" in mode:
            if not constr_var_part:
                constr_var_part += f"{'#'*85}\n"
                constr_var_part += f"# RC corners \n"
                constr_var_part += f"{'#'*85}\n\n"
            constr_dict_part[mode["name"].upper()] = mode["rc_corner"]

    fd.write(constr_var_part)

    if constr_dict_part != {}:
        __write_tcl_dict("TS_{}_RC_CORNERS".format(ts_get_design_top()), constr_dict_part, fd)
    else:
        ts_warning(TsWarnCode.WARN_PDK_10)


def __export_floorplan(fd):
    """
    """
    if "floorplan" not in TsGlobals.TS_DESIGN_CFG["design"]:
        ts_warning(TsWarnCode.WARN_PDK_5)
    else:
        fd.write("#" * 85 + "\n")
        fd.write("# Floorplan\n")
        fd.write("#" * 85 + "\n\n")
        fd.write("set TS_{}_FLOORPLAN {}\n".format(ts_get_design_top().upper(), TsGlobals.TS_DESIGN_CFG["design"]["floorplan"]))
        fd.write("\n")


def __export_map(fd):
    """
    """
    if "map" not in TsGlobals.TS_DESIGN_CFG["design"]:
        ts_warning(TsWarnCode.WARN_PDK_7)
    else:
        fd.write("#" * 85 + "\n")
        fd.write("# Map file\n")
        fd.write("#" * 85 + "\n\n")
        fd.write("set TS_{}_MAP {}\n".format(ts_get_design_top().upper(), TsGlobals.TS_DESIGN_CFG["design"]["map"]))
        fd.write("\n")

def __export_flow_dirs(fd):
    """
    Exports flow directories paths
    params: fd : file descriptor
    """

    fd.write("#" * 85 + "\n")
    fd.write("# Flow export directories\n")
    fd.write("#" * 85 + "\n\n")

    # Add ts-repo-rrot
    fd.write("set TS_REPO_ROOT $::env(TS_REPO_ROOT)\n")

    for item in TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"]:
        for key in item:
            # Supports relative/absolute paths to TS_REPO_ROOT
            fd.write(f"set TS_{str(key).upper()}_FLOW_EXPORT_DIR {ts_get_root_rel_path(item[key])}\n")
    fd.write("\n")


def export_design_config(path: str, args):
    """
    """
    fd = open(path, "w")
    __add_newline = lambda x: x + '\n'
    
    # write header
    fd.writelines(map(__add_newline, __get_design_config_header(TsGlobals.TS_EXP_VIEWS, args)))

    # Write design target (top entity)
    if args.add_top_entity:
        top_entity = ts_get_cfg()["targets"][TsGlobals.TS_DESIGN_CFG["design"]["target"]]["top_entity"].split(".")[-1]
        fd.write("set TS_DESIGN_NAME {}\n\n".format(top_entity))

    # Add flow directories paths
    __export_flow_dirs(fd)

    # Write RTL compile folders
    if args.add_syn_rtl_build_dirs:
        __export_rtl_build_dirs(fd)

    # Write views
    for view in TsGlobals.TS_EXP_VIEWS:
        
        fd.write("#" * 85 + "\n")
        fd.write("# View: {}\n".format(view))
        fd.write("#" * 85 + "\n\n")

        if view_has_corner(view):
            __export_view_with_corners(view, fd)
        else:
            __export_view_no_corners(view, fd)

    # Export constraints
    if args.add_constraints:
        __export_constraints(fd)

    # Export Floorplan
    if args.add_floorplan:
        __export_floorplan(fd)

    # Export map file
    if args.add_map:
        __export_map(fd)

    # Export spef
    if args.add_spef:
        __export_spef(fd)

    # Export Tlu+ files
    if args.add_tluplus:
        __export_tluplus(fd)
        __export_rc_corner(fd)

    fd.close()
