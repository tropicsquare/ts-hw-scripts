#!/usr/bin/env python3

###############################################################################
# Tropic Square mem map generate
#
# TODO: License
###############################################################################

__author__ = "Henri LHote"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Henri LHote"

from pathlib import Path

from internal.ts_hw_args import (
    TsArgumentParser,
    add_ts_common_args,
    add_ts_mem_map_generator_args,
)
from internal.ts_hw_logging import TsErrCode, ts_configure_logging, ts_throw_error
from internal.ts_mem_map_builder import (
    is_h_file,
    is_yaml_file,
    ordt_build_parms_file,
    render_yaml_parent,
)


def main():
    # Add script arguments
    parser = TsArgumentParser(description="Memory map generator script")
    add_ts_common_args(parser)
    add_ts_mem_map_generator_args(parser)
    args = parser.parse_args()

    ts_configure_logging(args)

    if args.latex_dir is None and args.xml_dir is None and args.h_file is None:
        ts_throw_error(
            TsErrCode.GENERIC,
            "No output file or directory was specified.\nAborting...",
        )

    # TODO check args via types, check they are dirs or files and their extensions

    render_yaml_parent(
        ordt_parms_file=args.ordt_parms,
        top_level_filepath=Path(args.source_file),
        lint=args.lint,
        latex_dir=Path(args.latex_dir) if args.latex_dir else None,
        xml_dir=Path(args.xml_dir) if args.xml_dir else None,
        c_header_file=Path(args.h_file) if args.h_file else None,
        do_not_clear=args.verbose,
    )


if __name__ == "__main__":
    main()
