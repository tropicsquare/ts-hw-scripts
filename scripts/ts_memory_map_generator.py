#!/usr/bin/env python3

###############################################################################
# Tropic Square memory map generator
#
# TODO: License
###############################################################################

__author__ = "Henri LHote"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Henri LHote"

import argparse
import hashlib
import logging
import re
import xml.etree.cElementTree as et
from datetime import datetime
from pathlib import Path
from typing import Callable, List, TypedDict

import argcomplete
import jinja2

__version__ = "0.3"
TOOL = Path(__file__)
DEFAULT_TEMPLATE = TOOL.parent / "internal/jinja_templates/memory_map.py.j2"


class InputField(TypedDict):
    shorttext: str
    lowidx: int
    width: int
    reset: int


class InputRegister(TypedDict):
    shorttext: str
    baseaddr: int
    field: List[InputField]


class InputRegion(TypedDict):
    shorttext: str
    baseaddr: int
    reg: List[InputRegister]


class InputDict(TypedDict):
    shorttext: str
    regset: List[InputRegion]


class Parser:
    @classmethod
    def parse_field(cls, node: et.Element) -> InputField:
        return {
            "shorttext": node.findtext("shorttext", ""),
            "lowidx": int(node.findtext("lowidx", "")),
            "width": int(node.findtext("width", "")),
            "reset": int(node.findtext("reset", "0x00"), base=16),
        }

    @classmethod
    def parse_register(cls, node: et.Element) -> InputRegister:
        return {
            "shorttext": node.findtext("shorttext", ""),
            "baseaddr": int(node.findtext("baseaddr", ""), base=16),
            "field": [cls.parse_field(child) for child in node.iter("field")],
        }

    @classmethod
    def parse_region(cls, node: et.Element) -> InputRegion:
        return {
            "shorttext": node.findtext("shorttext", ""),
            "baseaddr": int(node.findtext("baseaddr", ""), base=16),
            "reg": [cls.parse_register(child) for child in node.iter("reg")],
        }

    @classmethod
    def parse(cls, root: et.Element) -> InputDict:
        return {
            "shorttext": root.findtext("shorttext", ""),
            "regset": [cls.parse_region(child) for child in root.iter("regset")],
        }


class ContextField(TypedDict):
    name: str
    lowidx: int
    width: int
    reset: int


class ContextRegister(TypedDict):
    name: str
    address: int
    fields: List[ContextField]


class ContextRegion(TypedDict):
    name: str
    address: int
    registers: List[ContextRegister]


class ContextDict(TypedDict):
    name: str
    regions: List[ContextRegion]


class Converter:
    STARTS_WITH_NUMBER_REGEX = re.compile(r"\d+.*")

    @classmethod
    def format_name(cls, name: str) -> str:
        if cls.STARTS_WITH_NUMBER_REGEX.match(new_name := name.split()[0]):
            new_name = f"_{new_name}"
        return new_name.upper()

    @classmethod
    def convert_field(cls, field: InputField) -> ContextField:
        return {
            "name": cls.format_name(field["shorttext"]),
            "lowidx": field["lowidx"],
            "width": field["width"],
            "reset": field["reset"],
        }

    @classmethod
    def convert_register(cls, register: InputRegister) -> ContextRegister:
        return {
            "name": cls.format_name(register["shorttext"]),
            "address": register["baseaddr"],
            "fields": [cls.convert_field(field) for field in register["field"]],
        }

    @classmethod
    def convert_region(cls, region: InputRegion) -> ContextRegion:
        return {
            "name": cls.format_name(region["shorttext"]),
            "address": region["baseaddr"],
            "registers": [cls.convert_register(register) for register in region["reg"]],
        }

    @classmethod
    def convert(cls, root: InputDict) -> ContextDict:
        return {
            "name": cls.format_name(root["shorttext"]),
            "regions": [cls.convert_region(region) for region in root["regset"]],
        }


def configure_logging(verbose: int) -> None:
    try:
        level = [
            logging.WARNING,  # 0
            logging.INFO,  # 1
        ][verbose]
    except IndexError:
        level = logging.DEBUG  # >= 2
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


class HeaderDict(TypedDict):
    date: datetime
    tool: str
    version: str
    hash: str


def compute_sha256(filepath: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as fd:
        for byte_block in iter(lambda: fd.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def create_header(input_file: Path) -> HeaderDict:
    return {
        "date": datetime.now(),
        "tool": TOOL.name,
        "version": __version__,
        "hash": compute_sha256(input_file),
    }


def create_context(input_file: Path) -> ContextDict:
    return Converter.convert(Parser.parse(et.parse(input_file).getroot()))


def render(template_file: Path, *, header: HeaderDict, context: ContextDict) -> str:
    environment = jinja2.Environment(
        trim_blocks=False,
        lstrip_blocks=True,
        loader=jinja2.FileSystemLoader(template_file.parent),
    )
    return environment.get_template(template_file.name).render(
        header=header, context=context
    )


def generate_memory_map(
    input_file: Path,
    output_file: Path,
    template_file: Path = DEFAULT_TEMPLATE,
    verbose: int = 0,
):
    configure_logging(verbose)
    logging.debug("input_file = %s", input_file)
    logging.debug("output_file = %s", output_file)
    logging.debug("template_file = %s", template_file)

    logging.info("Processing input file.")
    header = create_header(input_file)
    logging.debug("header = %s", header)
    context = create_context(input_file)
    logging.debug("context = %s", context)
    logging.info("Input file processed.")

    logging.info("Rendering template.")
    content = render(template_file, header=header, context=context)
    logging.info("Template rendered.")

    logging.info("Writing output file.")
    with open(output_file, "w") as fd:
        fd.write(content)
    logging.info("Output file written.")


def get_cli_args():
    def _with_ext(ext: str) -> Callable[[Path], Path]:
        def _check(p: Path) -> Path:
            if not (e := "".join(p.suffixes)) == ext:
                raise OSError(f"Bad extension: {p}: '{e}'; should be '{ext}'")
            return p

        return _check

    def _file(fn: Callable[[Path], Path]) -> Callable[[str], Path]:
        def _check(s: str) -> Path:
            filepath = Path(s).resolve()
            if filepath.exists() and not filepath.is_file():
                raise IsADirectoryError(filepath)
            return fn(filepath)

        return _check

    def _existing_file(fn: Callable[[Path], Path]) -> Callable[[str], Path]:
        def _check(s: str) -> Path:
            filepath = Path(s).resolve()
            if not filepath.exists():
                raise FileNotFoundError(filepath)
            if not filepath.is_file():
                raise IsADirectoryError(filepath)
            return fn(filepath)

        return _check

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s version {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity. Defaults to warning level.",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=_existing_file(_with_ext(".xml")),
        required=True,
        help="XML input file",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=_file(_with_ext(".py")),
        required=True,
        help="Python output file",
    )
    parser.add_argument(
        "-t",
        "--template-file",
        type=_existing_file(_with_ext(".py.j2")),
        default=_existing_file(_with_ext(".py.j2"))(str(DEFAULT_TEMPLATE)),
        help="Template file. Defaults to %(default)s.",
    )
    argcomplete.autocomplete(parser)

    return vars(parser.parse_args())


if __name__ == "__main__":
    generate_memory_map(**get_cli_args())
