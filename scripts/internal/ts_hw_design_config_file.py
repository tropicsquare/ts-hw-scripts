# -*- coding: utf-8 -*-

####################################################################################################
# Functions for manipulating PDK config files
#
# TODO: License
####################################################################################################

import mmap
import os
import re

from schema import SchemaError

from .ts_grammar import (
    ALLOWED_DESIGN_OBJ_TYPES,
    GRAMMAR_DSG_CONFIG,
    GRAMMAR_PDK_CONFIG,
    PDK_VIEW_CONFIG,
)
from .ts_hw_common import (
    concat_keys,
    expand_vars,
    load_yaml_file,
    ts_get_file_rel_path,
    ts_get_root_rel_path,
    view_has_corner,
)
from .ts_hw_global_vars import TsGlobals
from .ts_hw_logging import (
    TsErrCode,
    TsInfoCode,
    TsWarnCode,
    ts_debug,
    ts_info,
    ts_script_bug,
    ts_throw_error,
    ts_warning,
)


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
    """ """
    rv = ""
    for obj in objs:
        rv += "{}({})".format(obj["name"], obj["version"])
        if obj != objs[-1]:
            rv += sep
    return rv


def mmap_size(filename):
    """
    Returns True if given word in bytes is located in a file
    :param filename: name of file
    :param word : searched word in bytes
    """
    with open(filename, mode="r") as f:
        with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as m:
            return m.size()


def mmap_search_word(filename, word, index):
    """
    Returns True if given word in bytes is located in a file
    :param filename: name of file
    :param word : searched word in bytes
    """
    with open(filename, mode="r") as f:
        with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as m:
            m.seek(index)
            return m.find(word)


def mmap_read_line(filename, index):
    """
    Returns whole line from the file
    :param filename: name of file
    :param line : line int
    """
    if index > 0:
        with open(filename, mode="r") as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as m:
                m.seek(index)
                return str(m.readline())
    else:
        return str("")


def __check_valid_opcond_corners(pdk_cfg: dict, obj: dict):
    """
    Returns True if given object has valid operation condition "opcond" for given PDK within a given librerty file
    :param pdk_cfg: PDK configuration dictionary
    :param obj: Object to check (ip, std_cells entry)
    """
    # Test pair opcond with its coexistating liberty file and search opcond within liberty
    # If pairing cannot be done then report if correspondigly
    for corner in pdk_cfg["corners"]:
        opcond = obj.get("opcond", {}).get(corner, {})
        liberty = obj.get("views", {}).get("nldm_lib", {}).get(corner, {})
        # check that definitions even exist
        if opcond and liberty:
            # set limits
            index_max = mmap_size(liberty)
            # initialize
            index = 0
            check = None
            # There could be several opcond definitions in a signle library file
            # It is important to search thru a file until either opcond matching or end of file
            while index < index_max:
                # Check existance of operation conditions in a file - return character index (see method mmap.search())
                index = mmap_search_word(
                    liberty, bytes(f"operating_conditions", "utf-8"), index
                )
                # Return line as a string
                line = str(mmap_read_line(liberty, index))
                # Increase search character for mmap.seek() purpose - infinite looping problem
                index = index + len(line)
                regex = re.compile(f"{opcond}")
                check = regex.search(line)
                if check is not None or index < 0:
                    # If opcond matchig the search - end it here, otherwise search thru a file
                    # If operating_conditions not matching at all >> -1 of index value
                    index = index_max
            if check is None:
                ts_throw_error(TsErrCode.ERR_PDK_23, opcond, liberty)


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
                    ts_throw_error(
                        TsErrCode.ERR_PDK_4,
                        corner,
                        "{}.{}".format(pdk_cfg["name"], obj["name"]),
                        "','".join(pdk_cfg["corners"].keys()),
                    )


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
                    ts_throw_error(
                        TsErrCode.ERR_PDK_5,
                        "{}.{}.{}".format(pdk_cfg["name"], obj["name"], corner_name),
                        corner_path,
                    )

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
                    ts_throw_error(
                        TsErrCode.ERR_PDK_5,
                        "{}.{}".format(pdk_cfg["name"], obj["name"]),
                        item,
                    )
        else:
            obj["views"][view_name] = ts_get_file_rel_path(pdk_cfg_path, view)
            if not os.path.exists(obj["views"][view_name]):
                ts_throw_error(
                    TsErrCode.ERR_PDK_5,
                    "{}.{}".format(pdk_cfg["name"], obj["name"]),
                    view,
                )


def __check_obj_duplicities(pdk, obj, obj_type, obj_type_name):
    """ """
    # Check duplicities with the same version
    for obj_2 in pdk[obj_type]:
        if (
            (obj_2 is not obj)
            and (obj["name"] == obj_2["name"])
            and (obj["version"] == obj_2["version"])
        ):
            ts_throw_error(
                TsErrCode.ERR_PDK_12, obj_type_name, obj["name"], obj["version"]
            )


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

                ts_info(
                    TsInfoCode.GENERIC,
                    "   Loading {}: '{}' version '{}'".format(
                        obj_type_name, obj["name"], obj["version"]
                    ),
                )
                __check_valid_opcond_corners(pdk, obj)
                __check_valid_view_corners(pdk, obj)
                __validate_views_exist(pdk, obj, path)
                __check_obj_duplicities(pdk, obj, obj_type, obj_type_name)


def __check_pdk_exists(pdk_name: str):
    """ """
    ts_debug("Checking PDK: '{}' exists.")
    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk["name"] == pdk_name:
            ts_debug("PDK: '{}' found.")
            return

    ts_throw_error(
        TsErrCode.ERR_PDK_6, pdk_name, concat_keys(TsGlobals.TS_PDK_CFGS, "name", "','")
    )


def __get_target_pdk():
    """ """
    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk["name"] == TsGlobals.TS_DESIGN_CFG["design"]["pdk"]:
            return pdk
    ts_script_bug(
        "Unknown PDK '{}' to obtain. Did you load PDK config properly?".format(
            TsGlobals.TS_DESIGN_CFG["design"]["name"]
        )
    )


def __check_flow_dirs_exists():
    """
    Check existance of flow directories
    """
    ts_debug("Checking flow dirs paths existance")
    if "flow_dirs" in TsGlobals.TS_DESIGN_CFG["design"]:
        for key in TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"].keys():
            # Supports relative/absolute paths to TS_REPO_ROOT
            if os.path.exists(
                ts_get_root_rel_path(
                    TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"][key]
                )
            ):
                ts_debug(
                    f" Flow directory exists -{key}: {TsGlobals.TS_DESIGN_CFG['design']['flow_dirs'][key]}"
                )
            else:
                ts_throw_error(
                    TsErrCode.ERR_PDK_19,
                    key,
                    ts_get_root_rel_path(
                        TsGlobals.TS_DESIGN_CFG["design"]["flow_dirs"][key]
                    ),
                )


def __check_std_cells_valid():
    """ """
    ts_debug("Checking standard cells")
    if len(TsGlobals.TS_DESIGN_CFG["design"]["std_cells"]) != 1:
        ts_throw_error(
            TsErrCode.ERR_PDK_14, str(TsGlobals.TS_DESIGN_CFG["design"]["std_cells"])
        )

    cells = TsGlobals.TS_DESIGN_CFG["design"]["std_cells"][0]
    std_cells_name = list(cells.keys())[0]
    std_cells_version = list(cells.values())[0]
    target_pdk_name = TsGlobals.TS_DESIGN_CFG["design"]["pdk"]

    for pdk in TsGlobals.TS_PDK_CFGS:
        if pdk["name"] == target_pdk_name:
            for std_cell in pdk["std_cells"]:
                if (
                    std_cell["name"] == std_cells_name
                    and std_cell["version"] == std_cells_version
                ):
                    ts_debug(
                        "Standard cells '{}' version '{}' checked OK".format(
                            std_cells_name, std_cells_version
                        )
                    )
                    return

    ts_throw_error(
        TsErrCode.ERR_PDK_7,
        target_pdk_name,
        std_cells_name,
        std_cells_version,
        __concat_available_objects(__get_target_pdk()["std_cells"], "','"),
    )


def __check_used_ips_valid():
    """ """
    if "ips" in TsGlobals.TS_DESIGN_CFG["design"]:
        tgt_pdk = __get_target_pdk()
        for used_ip in TsGlobals.TS_DESIGN_CFG["design"]["ips"]:
            ip_name = list(used_ip.keys())[0]
            ip_version = list(used_ip.values())[0]
            if "ips" not in tgt_pdk:
                ts_throw_error(TsErrCode.ERR_PDK_9, ip_name, tgt_pdk["name"])

            found = False
            for available_ip in tgt_pdk["ips"]:
                if (
                    available_ip["name"] == ip_name
                    and available_ip["version"] == ip_version
                ):
                    found = True

            if not found:
                ts_throw_error(
                    TsErrCode.ERR_PDK_8,
                    ip_name,
                    ip_version,
                    tgt_pdk["name"],
                    __concat_available_objects(tgt_pdk["ips"], "','"),
                )


def __check_modes_valid():
    """ """
    for i, mode in enumerate(TsGlobals.TS_DESIGN_CFG["design"]["modes"]):
        ts_debug("Checking design mode: {}".format(mode["name"]))
        if mode["corner"] not in __get_target_pdk()["corners"]:
            ts_throw_error(
                TsErrCode.ERR_PDK_10,
                mode["name"],
                mode["corner"],
                __get_target_pdk()["name"],
                "','".join(__get_target_pdk()["corners"].keys()),
            )

        if "constraints" in mode:
            if os.path.exists(ts_get_root_rel_path(mode["constraints"])):
                TsGlobals.TS_DESIGN_CFG["design"]["modes"][i][
                    "constraints"
                ] = ts_get_root_rel_path(mode["constraints"])
            else:
                ts_throw_error(
                    TsErrCode.ERR_PDK_11,
                    TsGlobals.TS_DESIGN_CFG["design"]["modes"][i]["constraints"],
                    mode["name"],
                )

        # There is no way how to test spef due to various sources of spef file locations
        # Existance of the file shall be tested in a flow itself because it depends on a usage of --source switch
        # if "spef" in mode:
        #    TsGlobals.TS_DESIGN_CFG["design"]["modes"][i]["spef"] = mode["spef"]

        if "tluplus" in mode:
            if os.path.exists(ts_get_root_rel_path(mode["tluplus"])):
                TsGlobals.TS_DESIGN_CFG["design"]["modes"][i][
                    "tluplus"
                ] = ts_get_root_rel_path(mode["tluplus"])
            else:
                ts_throw_error(
                    TsErrCode.ERR_PDK_21,
                    TsGlobals.TS_DESIGN_CFG["design"]["modes"][i]["tluplus"],
                    mode["name"],
                )

        # There is no need to check valid rc_corner string, it is not pointing to any particular file
        if "rc_corner" in mode:
            TsGlobals.TS_DESIGN_CFG["design"]["modes"][i]["rc_corner"] = mode[
                "rc_corner"
            ]


def __filter_modes_usage(flow_type):
    tmp = []
    for i, mode in enumerate(TsGlobals.TS_DESIGN_CFG["design"]["modes"]):

        # If "usage" is not defined, treat the mode as if enabled for given flow type.
        # With this behavior, it is backwards compatible, and also allows setting
        # up small block level synthesis without defining "usage"
        if (("usage" not in mode) or flow_type in mode["usage"]):
            tmp.append(TsGlobals.TS_DESIGN_CFG["design"]["modes"][i])
    if tmp:
        TsGlobals.TS_DESIGN_CFG["design"]["modes"] = tmp.copy()
        ts_debug("Filtered modes {}".format(TsGlobals.TS_DESIGN_CFG["design"]["modes"]))


def __check_global_design_attrs_valid():
    """ """

    # Check global constraints files
    if "constraints" in TsGlobals.TS_DESIGN_CFG["design"]:
        constrs = TsGlobals.TS_DESIGN_CFG["design"]["constraints"]
        if type(constrs) == str:
            if not os.path.exists(ts_get_root_rel_path(constrs)):
                ts_throw_error(TsErrCode.ERR_PDK_16, constrs)
            TsGlobals.TS_DESIGN_CFG["design"]["constraints"] = ts_get_root_rel_path(
                constrs
            )

        elif type(constrs) == list:
            for i, constr_file in enumerate(constrs):
                if not os.path.exists(ts_get_root_rel_path(constr_file)):
                    ts_throw_error(TsErrCode.ERR_PDK_16, constr_file)
                TsGlobals.TS_DESIGN_CFG["design"]["constraints"][
                    i
                ] = ts_get_root_rel_path(constr_file)

    # Check floorplan keyword
    if "floorplan" in TsGlobals.TS_DESIGN_CFG["design"]:
        fp = TsGlobals.TS_DESIGN_CFG["design"]["floorplan"]
        if not os.path.exists(ts_get_root_rel_path(fp)):
            ts_throw_error(TsErrCode.ERR_PDK_17, fp)
        TsGlobals.TS_DESIGN_CFG["design"]["floorplan"] = ts_get_root_rel_path(fp)

    # Check map keyword
    if "map" in TsGlobals.TS_DESIGN_CFG["design"]:
        fp = TsGlobals.TS_DESIGN_CFG["design"]["map"]
        if not os.path.exists(ts_get_root_rel_path(fp)):
            ts_throw_error(TsErrCode.ERR_PDK_20, fp)
        TsGlobals.TS_DESIGN_CFG["design"]["map"] = ts_get_root_rel_path(fp)

    # Check tech keyword
    if "tech" in TsGlobals.TS_DESIGN_CFG["design"]:
        fp = TsGlobals.TS_DESIGN_CFG["design"]["tech"]
        if not os.path.exists(ts_get_root_rel_path(fp)):
            ts_throw_error(TsErrCode.ERR_PDK_22, fp)
        TsGlobals.TS_DESIGN_CFG["design"]["tech"] = ts_get_root_rel_path(fp)


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
    __check_flow_dirs_exists()
    __check_std_cells_valid()
    __check_used_ips_valid()
    __check_modes_valid()
    __check_global_design_attrs_valid()


def filter_design_config_file(args):
    """
    Remove filtered objects from TS_DESIGN_CFG when applied
    """
    if args.filter_mode_usage:
        __filter_modes_usage(args.filter_mode_usage)


def check_export_view_types(args):
    """ """
    allowed_views = [str(x.schema) for x in list(PDK_VIEW_CONFIG.schema.keys())]
    ts_debug("Allowed views are: {}".format(allowed_views))
    for exp_view in TsGlobals.TS_EXP_VIEWS:
        found = False
        for golden_view in allowed_views:
            if str(exp_view) == golden_view:
                found = True
        if not found:
            ts_throw_error(
                TsErrCode.ERR_PDK_13, exp_view, "','".join(list(allowed_views))
            )


def print_pdk_obj(obj, args):
    """ """
    print("        - {}({})".format(obj["name"], obj["version"]))
    if args.verbose > 1:
        if "vendor" in obj:
            print("             Vendor: {}".format(obj["vendor"]))

        print("             Views:")
        for view_name, view_val in obj["views"].items():
            print("                 {}:".format(view_name))
            if type(view_val) == str:
                print("                     - {}".format(view_val))
            elif type(view_val) == list:
                for view_item in view_val:
                    print("                     - {}".format(view_item))
            elif type(view_val) == dict:
                for key in view_val.keys():
                    print("                     {}: {}".format(key, view_val[key]))
        print("")

    elif args.verbose > 0:
        if "vendor" in obj:
            print("               Vendor: {}".format(obj["vendor"]))
        print(
            "               Available views: {}".format(
                ", ".join(list(obj["views"].keys()))
            )
        )
        print("")
