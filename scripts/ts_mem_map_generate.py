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

from argparse import ArgumentTypeError
from pathlib import Path
from typing import Callable

from internal.ts_hw_args import TsArgumentParser, add_ts_common_args
from internal.ts_mem_map_builder import ts_render_yaml


def get_cli_args():
    def _with_ext(*ext: str) -> Callable[[Path], Path]:
        def _check(p: Path) -> Path:
            if p.suffix not in ext:
                raise ArgumentTypeError(f"{p}: extension not in {ext}.")
            return p

        return _check

    def _file(fn: Callable[[Path], Path]) -> Callable[[str], Path]:
        def _check(s: str) -> Path:
            if (p := Path(s)).exists() and not p.is_file():
                raise ArgumentTypeError(f"{p} is not a file.")
            return fn(p)

        return _check

    def _existing_file(fn: Callable[[Path], Path]) -> Callable[[str], Path]:
        def _check(s: str) -> Path:
            if not (p := Path(s)).exists():
                raise ArgumentTypeError(f"{p} not found.")
            if not p.is_file():
                raise ArgumentTypeError(f"{p} is not a file.")
            return fn(p)

        return _check

    def _dir(s: str) -> Path:
        if (p := Path(s)).exists() and not p.is_dir():
            raise ArgumentTypeError(f"{p} is not a dir.")
        return p

    parser = TsArgumentParser(description="Memory map generator script")

    add_ts_common_args(parser)

    parser.add_argument(
        "--xml-dir",
        type=_dir,
        help="XML output directory",
        metavar="DIR",
    )
    parser.add_argument(
        "--latex-dir",
        type=_dir,
        help="Latex output directory",
        metavar="DIR",
    )
    parser.add_argument(
        "--h-file",
        type=_file(_with_ext(".h")),
        help="C header output file",
        metavar="FILE",
    )
    parser.add_argument(
        "--source-file",
        type=_existing_file(_with_ext(".yml", ".yaml")),
        required=True,
        help="TASSIC memory map input file",
        metavar="FILE",
    )
    parser.add_argument(
        "--ordt-parms",
        type=_file(_with_ext(".parms")),
        help="Overrides the default parameters file for ORDT XML output.",
        metavar="FILE",
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Script will refuse overlapping address ranges.",
    )

    args = parser.parse_args()

    if not any((args.latex_dir, args.xml_dir, args.h_file)):
        parser.error(
            "At least one of --latex-dir, --xml-dir or --h-file must be given."
        )

    return args


if __name__ == "__main__":
    args = get_cli_args()

    args_dict = vars(args)
    args_dict.pop("no_color")
    args_dict["do_not_clear"] = args_dict["verbose"]

    ts_render_yaml(**args_dict)
