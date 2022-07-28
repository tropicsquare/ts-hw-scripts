# -*- coding: utf-8 -*-

####################################################################################################
# Functions for manipulating PDK config files
#
# TODO: License
####################################################################################################

import os
import contextlib
from schema import SchemaError

from .ts_hw_common import *
from .ts_grammar import *


def __load_pdk_config_file(pdk_cfg_path: str):
    """
    Loads PDK configuration file
    :param pdk_cfg_path: Config file path
    :return: Config file YAML object
    """
    ts_info(TsInfoCode.INFO_PDK_0, pdk_cfg_path)
    ts_debug("Loading PDK config file: {}".format(pdk_cfg_path))
    cfg = expand_vars(load_yaml_file(pdk_cfg_path))
    ts_debug("PDK config file loaded!")
    return cfg


def __concat_available_objects(objs: list, sep: str):
    """
    """
    rv = ""
    for obj in objs:
        rv += "{}({})".format(obj["name"], obj["version"])
        if obj != objs[-1]:
            rv += sep
    return rv


def __check_valid_view_corners(pdk_cfg: dict, obj: dict):
    """
    Returns True if given object has valid corners for given PDK
    :param pdk_cfg: PDK configuration dictionary
    :param obj: Object to check (ip, std_cells entry)
    """
    for view_name, view in obj["views"].items():
        if view_has_corner(view_name):
            for corner in view:
                ts_debug("Checking corner '{}' for view '{}'".format(corner, view))
                if corner not in pdk_cfg["corners"]:
                    ts_throw_error(TsErrCode.ERR_PDK_4, corner, "{}.{}".format(
                        pdk_cfg["name"], obj["name"]), "','".join(pdk_cfg["corners"].keys()))


def __validate_views_exist(pdk_cfg: dict, obj: dict, pdk_cfg_path: str):
    """
    Expands paths to views relative to 'pdk_cfg_path' and checks that these view files exist.
    :param pdk_cfg:
    :param obj:
    :param pdk_cfg_path:
    """
    for view_name, view in obj["views"].items():
        ts_debug("Checking view exists: {} for: {}".format(view_name, obj["name"]))
        if view_has_corner(view_name):

            # Check valid corners are referenced
            for corner_name, corner_path in view.items():
                view[corner_name] = ts_get_file_rel_path(pdk_cfg_path, corner_path)
                if not os.path.exists(view[corner_name]):
                     ts_throw_error(TsErrCode.ERR_PDK_5, "{}.{}.{}".format(
                         pdk_cfg["name"], obj["name"], corner_name), corner_path)

            # Check all corners are defined for all views which shall have corner
            for gold_corner in pdk_cfg["corners"]:
                found = False
                for corner_name in view.keys():
                    if corner_name == gold_corner:
                        found = True
                if not found:
                    ts_warning(TsWarnCode.WARN_PDK_2, gold_corner, obj["name"])

        elif type(view) == list:
            for i, item in enumerate(view):
                view[i] = ts_get_file_rel_path(pdk_cfg_path, item)
                if not os.path.exists(view[i]):
                    ts_throw_error(TsErrCode.ERR_PDK_5, "{}.{}".format(
                        pdk_cfg["name"], obj["name"]), item)
        else:
            obj["views"][view_name] = ts_get_file_rel_path(pdk_cfg_path, view)
            if not os.path.exists(obj["views"][view_name]):
                ts_throw_error(TsErrCode.ERR_PDK_5, "{}.{}".format(
                    pdk_cfg["name"], obj["name"]), view)


def __check_obj_duplicities(pdk, obj, obj_type, obj_type_name):
    """
    """
    # Check duplicities with the same version
    for obj_2 in pdk[obj_type]:
        if (obj_2 is not obj) and \
            (obj["name"] == obj_2["name"]) and \
            (obj["version"] == obj_2["version"]):
            ts_throw_error(TsErrCode.ERR_PDK_12, obj_type_name, obj["name"], obj["version"])   


def __check_pdk_config_file(pdk_cfg_file: dict, path: str):
    """
    Loads PDK config file and checks if PDK config file is valid
    :param pdk_cfg_file: Loaded PDK config file dictionary
    :param path: Path to the file
    """

    # Check grammar of PDK config file
    try:
        GRAMMAR_PDK_CONFIG.validate(pdk_cfg_file)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_PDK_0, e, path)

    # Check each PDK for valid semantic information
    pdk = pdk_cfg_file
    ts_info(TsInfoCode.INFO_PDK_4, pdk["name"])
    for obj_type in ALLOWED_DESIGN_OBJ_TYPES:
        if obj_type in pdk:
            for obj in pdk[obj_type]:

                if obj_type == "std_cells":
                    obj_type_name = "standard cells"
                else:
                    obj_type_name = "IP"

                ts_info(TsInfoCode.GENERIC, "   Loading {}: '{}' version '{}'".format(obj_type_name, obj["name"], obj["version"]))
                __check_valid_view_corners(pdk, obj)
                __validate_views_exist(pdk, obj, path)
                __check_obj_duplicities(pdk, obj, obj_type, obj_type_name)


def __check_pdk_exists(pdk_name: str):
    """
    """
    ts_debug("Checking PDK: '{}' exists.")
    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk["name"] == pdk_name:
            ts_debug("PDK: '{}' found.")
            return

    ts_throw_error(TsErrCode.ERR_PDK_6, pdk_name, concat_keys(TsGlobals.TS_PDK_CFGS, "name", "','"))


def __get_target_pdk():
    """
    """
    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk["name"] == TsGlobals.TS_DESIGN_CFG["design"]["pdk"]:
            return pdk
    ts_script_bug("Unknown PDK '{}' to obtain. Did you load PDK config properly?".format(
        TsGlobals.TS_DESIGN_CFG["design"]["name"]))


def __check_std_cells_valid():
    """
    """
    ts_debug("Checking standard cells")    
    if len(TsGlobals.TS_DESIGN_CFG["design"]["std_cells"]) != 1:
        ts_throw_error(TsErrCode.ERR_PDK_14, str(TsGlobals.TS_DESIGN_CFG["design"]["std_cells"]))

    cells = TsGlobals.TS_DESIGN_CFG["design"]["std_cells"][0]
    std_cells_name = list(cells.keys())[0]
    std_cells_version = list(cells.values())[0]
    target_pdk_name = TsGlobals.TS_DESIGN_CFG["design"]["pdk"]

    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk["name"] == target_pdk_name:
            for std_cell in pdk["std_cells"]:
                if std_cell["name"] == std_cells_name and \
                   std_cell["version"] == std_cells_version:
                    ts_debug("Standard cells '{}' version '{}' checked OK".format(
                              std_cells_name, std_cells_version))
                    return

    ts_throw_error(TsErrCode.ERR_PDK_7, target_pdk_name, std_cells_name, std_cells_version,
                    __concat_available_objects(__get_target_pdk()["std_cells"], "','"))


def __check_used_ips_valid():
    """
    """
    if "ips" in TsGlobals.TS_DESIGN_CFG["design"]:
        tgt_pdk = __get_target_pdk()
        for used_ip in TsGlobals.TS_DESIGN_CFG["design"]["ips"]:
            ip_name = list(used_ip.keys())[0]
            ip_version = list(used_ip.values())[0]
            if "ips" not in tgt_pdk:
                ts_throw_error(TsErrCode.ERR_PDK_9, ip_name, tgt_pdk["name"])

            found = False
            for available_ip in tgt_pdk["ips"]:
                if available_ip["name"] == ip_name and \
                   available_ip["version"] == ip_version:
                    found = True

            if not found:
                ts_throw_error(TsErrCode.ERR_PDK_8, ip_name, ip_version, tgt_pdk["name"],
                                __concat_available_objects(tgt_pdk["ips"], "','"))


def __check_modes_valid():
    """
    """
    for i, mode in enumerate(TsGlobals.TS_DESIGN_CFG["design"]["modes"]):
        ts_debug("Checking design mode: {}".format(mode["name"]))
        if mode["corner"] not in __get_target_pdk()["corners"]:
            ts_throw_error(TsErrCode.ERR_PDK_10, mode["name"], mode["corner"], __get_target_pdk()["name"],
                            "','".join(__get_target_pdk()["corners"].keys()))

        TsGlobals.TS_DESIGN_CFG["design"]["modes"][i]["constraints"] = ts_get_root_rel_path(mode["constraints"])

        if not os.path.exists(TsGlobals.TS_DESIGN_CFG["design"]["modes"][i]["constraints"]):
            ts_throw_error(TsErrCode.ERR_PDK_11, TsGlobals.TS_DESIGN_CFG["design"]["modes"][i]["constraints"],
                            mode["name"])


def __check_global_design_attrs_valid():
    """
    """

    # Check global constraints files
    if "constraints" in TsGlobals.TS_DESIGN_CFG["design"]:
        constrs = TsGlobals.TS_DESIGN_CFG["design"]["constraints"]
        if type(constrs) == str:
            if not os.path.exists(ts_get_root_rel_path(constrs)):
                ts_throw_error(TsErrCode.ERR_PDK_16, constrs)
            TsGlobals.TS_DESIGN_CFG["design"]["constraints"] = ts_get_root_rel_path(constrs)

        elif type(constrs) == list:
            for i, constr_file in enumerate(constrs):
                if not os.path.exists(ts_get_root_rel_path(constr_file)):
                    ts_throw_error(TsErrCode.ERR_PDK_16, constr_file)
                TsGlobals.TS_DESIGN_CFG["design"]["constraints"][i] = ts_get_root_rel_path(constr_file)

    # Check floorplan keyword
    if "floorplan" in TsGlobals.TS_DESIGN_CFG["design"]:
        fp = TsGlobals.TS_DESIGN_CFG["design"]["floorplan"]
        if not os.path.exists(ts_get_root_rel_path(fp)):
            ts_throw_error(TsErrCode.ERR_PDK_17, fp)
        TsGlobals.TS_DESIGN_CFG["design"]["floorplan"] = ts_get_root_rel_path(fp)


def load_design_config_file(design_cfg_path: str):
    """
    Loads Design configuration file
    :param design_cfg_path: Config file path
    :return: Config file YAML object
    """
    ts_debug("Loading design config file: {}".format(design_cfg_path))
    cfg = load_yaml_file(design_cfg_path)
    ts_debug("Design config file loaded!")
    return cfg


def check_design_config_file_grammar(design_cfg_file: dict, path: str):
    """
    Checks if design config file is matching towards its grammar
    :param design_cfg_file: Loaded PDK config file dictionary
    :param path: Path to the file
    """
    try:
        GRAMMAR_DSG_CONFIG.validate(design_cfg_file)
    except SchemaError as e:
        ts_throw_error(TsErrCode.ERR_PDK_2, e, path)


def load_pdk_configs():
    """
    Walk through PDK configs in design config files and loads them
    """
    for pdk in TsGlobals.TS_DESIGN_CFG["pdk_configs"]:
        
        full_path = ts_get_root_rel_path(pdk)
        if not os.path.exists(full_path):
            ts_throw_error(TsErrCode.ERR_PDK_3, full_path)

        pdk_cfg = __load_pdk_config_file(full_path)
        __check_pdk_config_file(pdk_cfg, full_path)

        TsGlobals.TS_PDK_CFGS.append(pdk_cfg)


def validate_design_config_file():
    """
    Check that design config file is referencing valid objects from included PDK
    """
    __check_pdk_exists(TsGlobals.TS_DESIGN_CFG["design"]["pdk"])
    __check_std_cells_valid()
    __check_used_ips_valid()
    __check_modes_valid()
    __check_global_design_attrs_valid()


def check_export_view_types(args):
    """
    """
    allowed_views = [str(x.schema) for x in list(PDK_VIEW_CONFIG.schema.keys())]
    ts_debug("Allowed views are: {}".format(allowed_views))
    for exp_view in TsGlobals.TS_EXP_VIEWS:
        found = False
        for golden_view in allowed_views:
            if str(exp_view) == golden_view:
                found = True
        if not found:
            ts_throw_error(TsErrCode.ERR_PDK_13, exp_view, "','".join(list(allowed_views)))


def print_pdk_obj(obj, args):
    """
    """
    print("        - {}({})".format(obj["name"], obj["version"]))
    if args.verbose > 1:
        for view_name, view_val in obj["views"].items():
            print("             {}:".format(view_name))
            if type(view_val) == str:
                print("                 - {}".format(view_val))
            elif type(view_val) == list:
                for view_item in view_val:
                    print("                 - {}".format(view_item))
            elif type(view_val) == dict:
                for key in view_val.keys():
                    print("                 {}: {}".format(key, view_val[key]))

    elif args.verbose > 0:
        print("               Has views: {}".format(", ".join(list(obj["views"].keys()))))