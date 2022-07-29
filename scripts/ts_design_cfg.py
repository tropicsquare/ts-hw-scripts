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

import shutil
import os
import argcomplete

from internal import *

if __name__ == "__main__":

    init_signals_handler()

    parser = TsArgumentParser(description="PDK/Design configuration file setup script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_pdk_cfg_args(parser)
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

    if args.add_views:
        TsGlobals.TS_EXP_VIEWS = args.add_views.split(",")
        check_export_view_types(args)
        ts_info(TsInfoCode.INFO_PDK_5, args.exp_tcl_design_cfg)
        export_design_config(args.exp_tcl_design_cfg, args)

    if args.exp_tcl_file_dc:
        ts_print(f"Exporting dc_shell TCL file: {args.exp_tcl_file_dc}",
                    color=TsColors.PURPLE, big=True)
        export_dc_tcl(args.exp_tcl_file_dc)

    if args.exp_tcl_file_vivado:
        ts_print(f"Exporting vivado TCL file: {args.exp_tcl_file_vivado}",
                    color=TsColors.PURPLE, big=True)
        export_vivado_tcl(args.exp_tcl_file_vivado)

    sys.exit(0)

