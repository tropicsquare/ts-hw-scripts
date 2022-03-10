# -*- coding: utf-8 -*-

####################################################################################################
# Functions for loading source list files.
#
# TODO: License
####################################################################################################

import os
import yaml
import contextlib
from schema import SchemaError

from .ts_hw_common import *
from .ts_grammar import *


def __check_src_list_file(list_file: dict, path: str):
    """
    Checks if source list file is valid. Includes check of structure (allowed keywords) and
    presence of required keywords. Throws exception if not.
    :param list_file: Loaded list file dictionary
    :param gold: Golden dictionary
    :param path: Path to the list file
    """
    try:
        GRAMMAR_SRC_LST.validate(list_file)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_SLF_18, e, path)

    for file_dict in list_file["source_list"]:
        if "define" in file_dict and file_dict["file"].endswith(".vhd"):
            ts_throw_error(TsErrCode.ERR_SLF_17, file_dict["file"], path)


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

    ts_debug(str(local_cfg))


def __expand_include_dirs(file_dict: dict, list_file_path: str):
    """
    Expand local include directories (per-file) to absolute path!
    :param file_dict: Source file dictionary
    :param list_file_path: Path to source list file.
    """
    with contextlib.suppress(KeyError):
        file_dict["include_dirs"] = [ts_get_file_rel_path(list_file_path, inc_dir)
                                                for inc_dir in file_dict["include_dirs"]]


def __load_source_list_file(list_file_path: str, current_depth: int = 1) -> list:
    """
    Loads source list file.
    :param list_file_path: Path to source list file
    :return: List of files within a list file (flat)
    """
    ret_val = []

    check_list_file_present(list_file_path)
    ts_debug("Loading source list file: {}".format(list_file_path))

    # Check for maximal depth
    if current_depth >= TsGlobals.MAX_LIST_FILE_DEPTH:
        ts_throw_error(TsErrCode.ERR_SLF_4, TsGlobals.MAX_LIST_FILE_DEPTH)

    try:
        with open(list_file_path) as lf:
            list_file = yaml.safe_load(lf)
    except Exception as e:
        ts_throw_error(TsErrCode.ERR_SLF_1, list_file_path)

    ts_debug("Source list file is:")
    ts_debug(str(list_file))

    ts_debug("Checking list file for validity:")
    __check_src_list_file(list_file, list_file_path)
    ts_debug("List file valid!")

    # Get config keywords common for all files
    global_cfg = list_file.copy()
    del global_cfg["source_list"]

    # Load files themselves
    for file_dict in list_file["source_list"]:
        __merge_global_to_local_dict(global_cfg, file_dict)

        # Local file path
        file_path = ts_get_file_rel_path(list_file_path, file_dict["file"])

        # Recurse for nested list file, don't append to output
        if file_dict["file"].endswith(".yml"):
            ret_val.extend(__load_source_list_file(file_path, current_depth + 1))
            continue

        # Check that the file really exists
        if not os.path.exists(file_path):
            ts_throw_error(TsErrCode.ERR_SLF_5, file_dict["file"], list_file_path)

        file_dict["full_path"] = file_path
        file_dict["nest_level"] = current_depth

        __expand_include_dirs(file_dict, list_file_path)

        ts_debug("Returned FILE is: {}".format(str(file_dict)))
        ts_debug(str(ret_val.append(file_dict)))

    return ret_val


def load_source_list_files(design_target: str) -> list:
    """
    Loads source list files from a design target. Resolves nested list files recursively.
    :param design_target: Current design target
    :returns: Flattened list of source file dictionaries
    """
    _MAX_NESTING_LEVEL = 5
    def _get_all_sources_for_target(target, level=0):
        if level >= _MAX_NESTING_LEVEL:
            raise RecursionError(f"Maximum nesting level reached: {_MAX_NESTING_LEVEL}")
        sources = []
        for source in ts_get_cfg("targets")[target]["source_list_files"]:
            if source == target:
                raise RecursionError(f"Circular recursion: {target} includes itself")
            # source is either a yaml file
            if source.endswith(".yml"):
               sources.append(source)
            # or a target
            else:
                ts_info(TsInfoCode.INFO_CMN_25, source)
                try:
                    sources.extend(_get_all_sources_for_target(source, level + 1))
                except Exception:
                    ts_throw_error(TsErrCode.ERR_CMP_6, target, source)
        return sources

    target_cfg = ts_get_cfg("targets")[design_target]
    if target_cfg is None:
        ts_script_bug("Target whose source list file you are trying to load is empty!")

    source_lists = _get_all_sources_for_target(design_target)
    ts_debug("Source list are: {}".format(source_lists))

    ret_val = []
    for source_list_path in source_lists:
        ret_val.extend(__load_source_list_file(ts_get_root_rel_path(source_list_path)))

    return ret_val


def group_source_list_files_by_lib(src_list: list) -> dict:
    """
    Groups list of source files into a dictionary by library
    :param src_list: List of source files
    :return: Dictionary of source list files grouped by compilation library.
    """
    output_dict = {}
    for _file in src_list:
        if "file" not in _file:
            ts_script_bug("Each valid file in list file shall contain 'file' keyword!")
        if "library" not in _file:
            ts_script_bug("Each valid file in list file shall contain 'library' keyword!")

        output_dict.setdefault(_file["library"], [])
        output_dict[_file["library"]].append(_file)

    return output_dict


def print_source_file_list(print_full_path: bool = True):
    """
    Prints flat list of source files, organized by design library into which the source file is
    compiled.
    :param: print_full_path - True - prints full path of the file.
                              False - prints only relative path to its list file
    """
    ts_info(TsInfoCode.INFO_CMN_4)

    for lib, files in TsGlobals.TS_SIM_SRCS_BY_LIB.items():
        print(lib)
        for _file in files:
            if print_full_path:
                real_path = _file["full_path"]
            else:
                real_path = _file["file"]
            print("     - {}".format(real_path))
            # TODO: Consider different format of printing with nesting by hierarchy!
