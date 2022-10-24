#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from internal import *

def main():

    # Add script arguments
    parser = TsArgumentParser(description="Memory map generator script")
    add_ts_common_args(parser)
    add_ts_mem_map_generator_args(parser)

    args = parser.parse_args()
    ts_configure_logging(args)

    # Create output directory if the one specified doesn't exist
    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)

    # Set names of output files the same as top input file
    tmp = os.path.splitext(os.path.basename(args.source_file))[0]
    Path(os.path.join(args.output_dir, f'{tmp}.rdl')).touch()
    rdl_file = os.path.join(args.output_dir, f'{tmp}.rdl')
    xml_file = os.path.join(args.output_dir, f'{tmp}.xml')

    if args.ordt_parms is None:
        ordt_parms_filename = f'{tmp}.parms'
        ordt_parms_file = ordt_build_parms_file(args.output_dir, ordt_parms_filename)
    else:
        ordt_parms_file = args.ordt_parms

    render_yaml_parent(args.source_file)
    rdl_build_output(rdl_file, xml_file, ordt_parms_file)

if __name__ == "__main__":
    main()
