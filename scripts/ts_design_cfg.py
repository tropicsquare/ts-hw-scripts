#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square PDK configuration file processing script
#
# TODO: License
####################################################################################################

__author__ = "Ondrej Ille"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Ondrej Ille"

import sys

import argcomplete
from internal.ts_grammar import PDK_VIEW_CONFIG
from internal.ts_hw_args import (
    TsArgumentParser,
    add_cfg_files_arg,
    add_pdk_cfg_args,
    add_ts_common_args,
)
from internal.ts_hw_cfg_parser import (
    check_valid_design_target,
    do_design_config_init,
    do_sim_config_init,
)
from internal.ts_hw_common import init_signals_handler, ts_get_cfg, view_has_corner
from internal.ts_hw_design_config_file import check_export_view_types, print_pdk_obj
from internal.ts_hw_export import export_dc_tcl, export_design_config, export_vivado_tcl
from internal.ts_hw_global_vars import TsGlobals
from internal.ts_hw_logging import (
    TsColors,
    TsInfoCode,
    TsWarnCode,
    ts_configure_logging,
    ts_info,
    ts_print,
    ts_warning,
)
from internal.ts_hw_source_list_files import load_source_list_files

if __name__ == "__main__":

    init_signals_handler()

    parser = TsArgumentParser(description="PDK/Design configuration file setup script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_pdk_cfg_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Load config files, merge with args and check configuration
    # Pass design target directly from design config file so that we don't need to
    # pass it from command line
    do_design_config_init(args)
    setattr(args, "target", TsGlobals.TS_DESIGN_CFG["design"]["target"])
    do_sim_config_init(args)
    check_valid_design_target()
    load_source_list_files(ts_get_cfg("target"))

    if args.list_pdks:
        print("List of loaded PDKs:")
        for pdk in TsGlobals.TS_PDK_CFGS:
            print("   {}".format(pdk["name"]))
        sys.exit(0)

    if args.list_pdk_std_cells:
        print("List of available standard cells:")
        for pdk in TsGlobals.TS_PDK_CFGS:
            print("    {}:".format(pdk["name"]))
            for std_cell in pdk["std_cells"]:
                print_pdk_obj(std_cell, args)
        sys.exit(0)

    if args.list_pdk_ips:
        print("List of available IPs (hard macros):")
        for pdk in TsGlobals.TS_PDK_CFGS:
            print("    {}:".format(pdk["name"]))
            if "ips" in pdk:
                for ip in pdk["ips"]:
                    print_pdk_obj(ip, args)
            else:
                print("        No IPs in this PDK.")
        sys.exit(0)
    
    if args.list_supported_views:
        print("List of views supported by PDK / Design configs:")
        for view, view_value in PDK_VIEW_CONFIG.schema.items():
            #print(view)
            #print(view_value)
            #print(dir(view))
            if view_has_corner(str(view.schema)):
                corn = "Single view for each PDK corner"
            else:
                corn = "Single view, or list of views"
            print("    - {} : {}".format(view.schema.ljust(15), corn))

    if args.exp_tcl_file_dc:
        ts_print(f"Exporting dc_shell TCL file: {args.exp_tcl_file_dc}",
                    color=TsColors.PURPLE, big=True)
        export_dc_tcl(args.exp_tcl_file_dc)

    if args.exp_tcl_file_vivado:
        ts_print(f"Exporting vivado TCL file: {args.exp_tcl_file_vivado}",
                    color=TsColors.PURPLE, big=True)
        export_vivado_tcl(args.exp_tcl_file_vivado)

    if args.add_views:
        TsGlobals.TS_EXP_VIEWS = args.add_views.split(",")
        check_export_view_types(args)
        ts_info(TsInfoCode.INFO_PDK_5, args.exp_tcl_design_cfg)
        export_design_config(args.exp_tcl_design_cfg, args)
    else:
        ts_warning(TsWarnCode.WARN_PDK_6)

    sys.exit(0)

