#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
from pathlib import Path
from internal.ts_hw_args import (
    TsArgumentParser,
    add_ts_common_args,
    add_ts_mem_map_generator_args,
)
from internal.ts_hw_logging import TsErrCode, ts_configure_logging, ts_throw_error
from internal.ts_mem_map_builder import (
    is_yaml_file,
    is_h_file,
    ordt_build_parms_file,
    render_yaml_parent,
)

def main(raw_args=None):

    # Add script arguments
    parser = TsArgumentParser(description="Memory map generator script")
    add_ts_common_args(parser)
    add_ts_mem_map_generator_args(parser)
 
    args = parser.parse_args(raw_args)

    ts_configure_logging(args)

    if args.latex_dir is None and args.xml_dir is None and args.h_file is None:
        ts_throw_error(
            TsErrCode.GENERIC,
            "No output file or directory was specified.\nAborting...",
        )

    if args.latex_dir is not None and not os.path.isdir(args.latex_dir):
        os.makedirs(args.latex_dir)

    if args.xml_dir is not None and not os.path.isdir(args.xml_dir):
        os.makedirs(args.xml_dir)

    if args.h_file is not None and is_h_file(Path(args.h_file)):
        open(args.h_file, 'w').close()

    is_yaml_file(args.source_file)

    if args.xml_dir is not None and args.ordt_parms is None:
        ordt_parms_filename = f"{Path(args.source_file).stem}.parms"
        ordt_parms_path = os.path.join(args.xml_dir, ordt_parms_filename)
        ordt_build_parms_file(ordt_parms_path)
    else:
        ordt_parms_path = args.ordt_parms

    render_yaml_parent(
        ordt_parms_file=ordt_parms_path,
        top_level_filepath=args.source_file,
        lint=args.lint,
        latex_dir=args.latex_dir,
        xml_dir=args.xml_dir,
        c_header_file=args.h_file,
        do_not_clear = args.verbose,
    )


if __name__ == "__main__":
    main()
