#!/usr/bin/env python3

###############################################################################
# Tropic Square mem map generate
#
# For license see LICENSE file in repository root.
###############################################################################

__author__ = "Henri LHote"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Henri LHote"

from argparse import ArgumentTypeError
from pathlib import Path
from typing import Callable

from internal.ts_hw_args import TsArgumentParser, add_ts_common_args
from internal.ts_hw_logging import ts_configure_logging
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
        "--py-file",
        type=_file(_with_ext(".py")),
        help="Python output file",
        metavar="FILE",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force generation. If not set, the hash written in the output file - if it exists - is compared"
        "\nagainst the hash of the configuration. The output file is then regenerated upon mismatch.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = get_cli_args()

    ts_configure_logging(args)  # type: ignore

    args_dict = vars(args)
    args_dict.pop("no_color")
    args_dict["do_not_clear"] = bool(args_dict.pop("verbose"))

    ts_render_yaml(**args_dict)
