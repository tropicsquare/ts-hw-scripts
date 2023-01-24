# -*- coding: utf-8 -*-

####################################################################################################
# Functions for loading source list files.
#
# TODO: License
####################################################################################################

import contextlib
import os

from schema import SchemaError

from .ts_grammar import ALLOWED_DESIGN_OBJ_TYPES, GRAMMAR_SRC_LST
from .ts_hw_common import (
    expand_vars,
    get_pdk_obj,
    load_yaml_file,
    ts_get_cfg,
    ts_get_file_rel_path,
    ts_get_root_rel_path,
)
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsErrCode,
    TsInfoCode,
    ts_debug,
    ts_info,
    ts_print,
    ts_script_bug,
    ts_throw_error,
)


def __merge_global_to_local_dict(global_cfg: dict, local_cfg: dict):
    """
    Merges global dictionary to local dictionary, local one has priority in equal keys
    :param global_cfg: Global dictionary (Lower priority)
    :param local_cfg: Local dictionary (Higher priority)
    """
    for key, val in global_cfg.items():
        if key in local_cfg:
            # Merge dictionaries and lists
            if isinstance(val, dict):
                local_cfg[key].update(val)
            elif isinstance(val, list):
                local_cfg[key].extend(val)

        # Override keys which are not defined in local dict!
        else:
            local_cfg[key] = val

    ts_debug(local_cfg)


def __load_source_list_file(list_file_path: str, current_depth: int = 1) -> list:
    """
    Loads source list file.
    :param list_file_path: Path to source list file
    :return: List of files within a list file (flat)
    """
    ret_val = []

    ts_debug(f"Loading source list file: {list_file_path}")

    # Check for maximal depth
    if current_depth >= TsGlobals.MAX_LIST_FILE_DEPTH:
        ts_throw_error(TsErrCode.ERR_SLF_4, TsGlobals.MAX_LIST_FILE_DEPTH)

    list_file = load_yaml_file(list_file_path)
    ts_debug(f"Source list file is: {list_file}")

    ts_debug("Expanding environment variables of source list file")
    list_file = expand_vars(list_file)

    ts_debug("Checking list file for validity:")
    try:
        GRAMMAR_SRC_LST.validate(list_file)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_SLF_18, e, list_file_path)
    ts_debug("List file valid!")

    ts_debug("Merging compilation options in source file")
    root_comp_options = list_file.pop("comp_options", {})
    for k, v in root_comp_options.items():
        for file_dict in list_file["source_list"]:
            file_comp_options = file_dict.setdefault("comp_options", {})
            if k in file_comp_options:
                file_comp_options[k] = v + " " + file_comp_options[k]
            else:
                file_comp_options[k] = v
    ts_debug("Done")

    # Get config keywords common for all files
    global_cfg = list_file.copy()
    del global_cfg["source_list"]

    # Load files themselves
    for file_dict in list_file["source_list"]:
        __merge_global_to_local_dict(global_cfg, file_dict)

        # Local file path
        file_path = ts_get_file_rel_path(list_file_path, file_dict["file"])

        # Recurse for nested list file, don't append to output
        if file_path.endswith(".yml"):
            ret_val.extend(__load_source_list_file(file_path, current_depth + 1))
            continue

        # Check that the file really exists
        if not os.path.exists(file_path):
            ts_throw_error(TsErrCode.ERR_SLF_5, file_path, list_file_path)

        file_dict["full_path"] = file_path
        file_dict["nest_level"] = current_depth

        # Expand local include directories (per-file) to absolute path!
        with contextlib.suppress(KeyError):
            file_dict["include_dirs"] = [ts_get_file_rel_path(list_file_path, inc_dir)
                                            for inc_dir in file_dict["include_dirs"]]

        ts_debug(f"Returned file is: {file_dict}")
        ret_val.append(file_dict)

    return ret_val


def load_source_list_files(design_target: str):
    """
    Loads source list files from a design target. Resolves nested list files recursively.
    :param design_target: Current design target
    """
    _MAX_NESTING_LEVEL = 5
    def _get_all_sources_for_target(target, level=0):
        if level >= _MAX_NESTING_LEVEL:
            raise RecursionError(f"Maximum nesting level reached: {_MAX_NESTING_LEVEL}")
        sources = []
        for source in ts_get_cfg("targets")[target]["source_list_files"]:
            if source == target:
                raise RecursionError(f"Circular recursion: {target} includes itself")

            # Reference to SLF view of PDK object
            if source.startswith(":"):
                ts_debug("Searching PDK object source list file from: {}".format(source))
                
                # For backwards compatibility most of repositories do not have design config
                # available at the time of implementation! So we must avoid bug if we tried
                # to reference PDK object without any design config file loaded!
                if not TsGlobals.TS_DESIGN_CFG:
                    ts_throw_error(TsErrCode.ERR_SLF_21, source, target)

                # Search if YAML is hard macro referenced behav model view from used
                # IP cores
                split_name = source.split(":")
                while "" in split_name:
                    split_name.remove("")

                # Find PDK object matching to first word in the path
                pdk_obj = None
                for obj_type in ALLOWED_DESIGN_OBJ_TYPES:
                    if (obj_type in TsGlobals.TS_DESIGN_CFG["design"]):
                        for obj in TsGlobals.TS_DESIGN_CFG["design"][obj_type]:
                            obj_name = list(obj.keys())[0]
                            obj_version = list(obj.values())[0]
                            if split_name[0] == obj_name:
                                pdk_obj = get_pdk_obj(obj_type, obj_name, obj_version)

                if pdk_obj:
                    try:
                        found = False
                        
                        # Make sure we iterate list, slf view can be also only string!
                        avail_lst = pdk_obj["views"]["slf"]
                        if (type(avail_lst) != list):
                            avail_lst = [avail_lst]

                        for src in avail_lst:
                            if os.path.basename(src) == split_name[-1]:
                                ts_debug("Appending source list file: {} from PDK object: {}\n".format(src, pdk_obj["name"]))
                                sources.append(src)
                                found = True
                        if not found:
                            raise Exception
                    except:
                        if "slf" in pdk_obj["views"]:
                            filt = [os.path.basename(x) for x in pdk_obj["views"]["slf"]]
                        else:
                            filt = []
                        ts_throw_error(TsErrCode.ERR_SLF_20, split_name[-1], split_name[0], filt)
                    
                else:
                    ts_throw_error(TsErrCode.ERR_SLF_19, split_name[0], design_target)

                #except:
                #    pass
            
            # Regular YAML file
            elif source.endswith(".yml"):
                sources.append(source)

            # or a target
            else:
                ts_info(TsInfoCode.INFO_CMN_25, source)
                try:
                    sources.extend(_get_all_sources_for_target(source, level + 1))
                except Exception as e:
                    ts_throw_error(TsErrCode.GENERIC,
                                    f"An issue occurred while parsing target '{source}' "
                                    f"on which depends target '{target}': {e}")
        return sources

    target_cfg = ts_get_cfg("targets")[design_target]
    if target_cfg is None:
        ts_script_bug("Target whose source list file you are trying to load is empty!")

    source_lists = []
    #try:
    for source_list_path in _get_all_sources_for_target(design_target):
        # Remove duplicates
        if source_list_path not in source_lists:
            source_lists.append(source_list_path)
    #except Exception as e:
    #    ts_throw_error(TsErrCode.GENERIC,
    #                    f"An issue occurred while parsing target '{design_target}': {e}")

    ts_debug("Source list files are: {source_lists}")

    src_list = []
    for source_list_path in source_lists:
        if not source_list_path.startswith("::"):
            src_list.extend(__load_source_list_file(ts_get_root_rel_path(source_list_path)))

    # Create two lists of source files: flat and library-wise hierarchical
    TsGlobals.TS_SIM_SRCS = []
    TsGlobals.TS_SIM_SRCS_BY_LIB = {}
    for f in src_list:
        # Remove duplicates
        if f not in TsGlobals.TS_SIM_SRCS:
            TsGlobals.TS_SIM_SRCS.append(f)
            TsGlobals.TS_SIM_SRCS_BY_LIB.setdefault(f["library"], [])
            TsGlobals.TS_SIM_SRCS_BY_LIB[f["library"]].append(f)


def print_source_file_list(print_full_path: bool = True):
    """
    Prints flat list of source files, organized by design library
    :param: print_full_path - True - prints full path of the file.
                              False - prints only relative path to its list file
    """
    ts_print("List of available source files:")
    for lib, files in TsGlobals.TS_SIM_SRCS_BY_LIB.items():
        ts_print(lib,
                *map(lambda f: f["full_path"] if print_full_path else f["file"],
                    files),
                sep="\n\t- ")

def get_netlist_from_slf(list_file_path: str):
    """
    """
    src_list = __load_source_list_file(ts_get_root_rel_path(list_file_path))
    if os.path.exists(src_list[0]["full_path"]):
        return src_list[0]["full_path"]
    else:
        ts_throw_error(TsErrCode.GENERIC("netlist {} not found!".format(src_list[0]["full_path"])))