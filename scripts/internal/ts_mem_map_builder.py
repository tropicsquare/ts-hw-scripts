# -*- coding: utf-8 -*-

###################################################################################################
# Functions for generating memory map files.
#
# TODO: License
###################################################################################################

__author__ = "Henri LHote"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Henri LHote"

import fileinput
import logging
import os
import re
import shutil
import subprocess
import xml.etree.cElementTree as et
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property, partial
from hashlib import sha256
from itertools import chain, count
from pathlib import Path
from pprint import pformat
from tempfile import TemporaryDirectory
from typing import (
    Any,
    ClassVar,
    Container,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Pattern,
    Protocol,
    Set,
    TypedDict,
    Union,
)

import jinja2
import yaml
from typing_extensions import NotRequired, Self

from .__version__ import __version__

try:
    from .ts_grammar import GRAMMAR_MEM_MAP_CONFIG  # type: ignore

except ImportError:

    class GRAMMAR_MEM_MAP_CONFIG:
        @staticmethod
        def validate(_: Any):
            pass


TOOL = Path(__file__)
TEMPLATE_DIRECTORY = TOOL.parent / "jinja_templates"


class MemMapGenerateError(Exception):
    pass


# ############################## logging-related features #########################################


class NestedStructureLog:
    """Pretty-print a nested structure upon logging"""

    def __init__(self, struct: Any) -> None:
        self.struct = struct

    def __str__(self) -> str:
        if isinstance(self.struct, Node):
            return pformat(self.struct.to_dict(), sort_dicts=False)
        return pformat(self.struct, sort_dicts=False)


# ############################## file and dir-related functions ###################################


def _has_ext(file: Union[Path, str], *, extensions: Container[str]) -> bool:
    if isinstance(file, str):
        file = Path(file)
    return file.suffix in extensions


_is_yaml_file = partial(_has_ext, extensions=(".yml", ".yaml"))

_is_rdl_file = partial(_has_ext, extensions=(".rdl",))


def _remove_directory(dirpath: Path) -> None:
    logging.debug("Removing directory: %s", dirpath)
    shutil.rmtree(dirpath, ignore_errors=True)


def _create_directory(dirpath: Path) -> None:
    logging.debug("Creating directory: %s", dirpath)
    dirpath.mkdir(parents=True, exist_ok=True)


def compute_sha256(filepath: Path) -> str:
    _hash = sha256()
    with open(filepath, "rb") as fd:
        for byte_block in iter(lambda: fd.read(4096), b""):
            _hash.update(byte_block)
    return _hash.hexdigest()


def expand_envvars(path: str) -> str:
    """Expands environment variables in path, returns Path object."""
    expanded_path = os.path.expandvars(path)

    if "$" in path and Path(expanded_path) == Path(path):
        raise MemMapGenerateError(
            f"Environment variable(s) used but not defined in path ({path})"
        )

    return expanded_path


# ############################## file rendering ###################################################


class RenderFn(Protocol):
    def __call__(self, template_file: str, **kwargs: Any) -> str:
        ...


def create_render_fn() -> RenderFn:
    environment = jinja2.Environment(
        trim_blocks=False,
        lstrip_blocks=True,
        loader=jinja2.FileSystemLoader(TEMPLATE_DIRECTORY),
    )

    def _render(template_file: str, **kwargs: Any) -> str:
        if common := {"date", "tool", "version"} & set(kwargs.keys()):
            raise MemMapGenerateError(f"Keys '{common}' are reserved.")
        return environment.get_template(template_file).render(
            **kwargs,
            date=datetime.now(),
            tool=TOOL.stem.replace("_", " ").title(),
            version=__version__,
        )

    return _render


# ############################## ORDT-related functions ###########################################


def _ordt_run(
    source: Path, output: Path, parms: Path, arg: Literal["xml", "tslatexdoc"]
) -> None:
    command = f"ordt_run.sh -parms {parms} -{arg} {output} {source}"
    logging.info("Running ORDT command: %s", command)

    completed_process = subprocess.run(
        command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed_process.returncode != 0:
        logging.error(
            "ORDT returned the following error(s): \n%s",
            completed_process.stderr.decode(),
        )
        raise MemMapGenerateError(
            f"ORDT error: returncode = {completed_process.returncode}"
        )

    logging.warning("Built using ORDT: %s", output)


_ordt_generate_xml = partial(_ordt_run, arg="xml")

_ordt_generate_latex = partial(_ordt_run, arg="tslatexdoc")


def _ordt_build_parms_file(
    filepath: Path, base_address: int, render_fn: RenderFn
) -> None:
    """builds a parameters file with default parameters for ordt in the output directory"""
    content = render_fn("parms_file.parms.j2", top={"base_address": base_address})
    logging.info("Writing ORDT parms file: %s", filepath)
    with open(filepath, "w") as fd:
        fd.write(content)


# ############################## Data model #######################################################


class RegionsDict(TypedDict):
    name: str
    short_name: NotRequired[str]
    start_addr: int
    end_addr: int
    reg_map: NotRequired[str]
    regions: NotRequired[Union[List[Self], str]]


@dataclass(frozen=True)
class Node:
    MAX_NESTING_LEVEL: ClassVar[int] = 5
    name: str
    start_addr: int
    end_addr: int
    level: int
    source: Path
    short_name: str = ""
    reg_map: Optional[Path] = None
    parent: Optional[Self] = field(repr=False, default=None)
    children: List[Self] = field(init=False, default_factory=list)

    @classmethod
    def new(
        cls,
        cfg: RegionsDict,
        source: Path,
        level: int = 0,
        parent: Optional[Self] = None,
    ) -> Self:

        logging.warning("Creating new node: %s.", cfg["name"])
        logging.info(
            "with start address: 0x%08X and end address: 0x%08X",
            cfg["start_addr"],
            cfg["end_addr"],
        )

        node = cls(
            name=cfg["name"],
            start_addr=cfg["start_addr"],
            end_addr=cfg["end_addr"],
            level=level,
            source=source,
            short_name=cfg.get("short_name", ""),
            parent=parent,
        )

        if (level := level + 1) > cls.MAX_NESTING_LEVEL:
            error_path = [node.name] + [p.name for p in node.parents]
            logging.error(" -> ".join(reversed(error_path)))
            raise MemMapGenerateError(
                f"Nesting {level = } exceeds limit of {cls.MAX_NESTING_LEVEL}"
            )

        if (reg_map := cfg.get("reg_map")) is not None:
            assert cfg.get("regions") is None, "node should be a leaf"
            reg_map = expand_envvars(reg_map)
            if not _is_rdl_file(reg_map):
                raise MemMapGenerateError(f"{reg_map} should be an rdl file")
            logging.debug("Including RDL file: %s", reg_map)
            object.__setattr__(node, "reg_map", source.parent / reg_map)
            return node

        object.__setattr__(
            node,
            "children",
            cls._load_regions(cfg.get("regions", []), source, level, node),
        )
        return node

    @classmethod
    def _load_regions(
        cls,
        regions: Union[List[RegionsDict], str],
        source: Path,
        level: int,
        parent: Self,
    ) -> List[Self]:
        if isinstance(regions, str):
            filepath = source.parent / expand_envvars(regions)
            logging.warning("Found new memory sub-region: %s.", regions)
            cfg = cls.load_yaml(filepath)
            assert cfg.get("reg_map") is None, "node should be a leaf"
            return cls._load_regions(cfg.get("regions", []), filepath, level, parent)

        return [cls.new(region, source, level, parent) for region in regions]

    @classmethod
    def load_tree(cls, filepath: Path) -> Self:
        root_cfg = cls.load_yaml(filepath)
        if root_cfg.get("regions") is None:
            raise MemMapGenerateError(
                f"Top level in '{filepath}' does not define 'regions' key"
            )
        return cls.new(root_cfg, filepath)

    @staticmethod
    def load_yaml(filepath: Path) -> RegionsDict:
        if not _is_yaml_file(filepath):
            raise MemMapGenerateError(f"{filepath} should be a yaml file")

        logging.debug("Opening YAML file: %s", filepath)
        with open(filepath) as fd:
            content = yaml.safe_load(fd)

        GRAMMAR_MEM_MAP_CONFIG.validate(content)
        logging.debug("New region validated: %s.", content["name"])
        return content

    @property
    def abs_start_addr(self) -> int:
        if self.parent is None:
            return self.start_addr
        return self.start_addr + self.parent.abs_start_addr

    @property
    def abs_end_addr(self) -> int:
        if self.parent is None:
            return self.end_addr
        return self.end_addr + self.parent.abs_start_addr

    @property
    def parents(self) -> List[Self]:
        if self.parent is None:
            return []
        return [self.parent] + self.parent.parents

    def repr_hierarchy(self) -> str:
        l = ["{}[L{}] {}".format("\t" * self.level, self.level, self.name)]
        l.extend(child.repr_hierarchy() for child in self.children)
        return "\n".join(l)

    @cached_property
    def configuration_hash(self) -> str:
        def _get_sources(node: Self) -> Set[Path]:
            _s = {node.source}
            if node.reg_map is not None:
                _s.add(node.reg_map)
            return _s | set(
                chain.from_iterable(_get_sources(child) for child in node.children)
            )

        def _compute_sha256(filepaths: List[Path]) -> str:
            _hash = sha256()
            for filepath in filepaths:
                with open(filepath, "rb") as fd:
                    for byte_block in iter(lambda: fd.read(4096), b""):
                        _hash.update(byte_block)
            return _hash.hexdigest()

        return _compute_sha256(sorted(_get_sources(self))).upper()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_addr": f"0x{self.start_addr:08X}",
            "end_addr": f"0x{self.end_addr:08X}",
            "level": self.level,
            "source": str(self.source),
            "short_name": self.short_name,
            "reg_map": str(self.reg_map),
            # no "parent" key here as it causes infinite recursion error
            "children": [child.to_dict() for child in self.children],
        }


# ############################## Up-to-date function ##############################################


def is_up_to_date(filepath: Path, tree: Node, regex: Pattern[str]) -> bool:
    _MAX_SCANNED_LINES = 10
    try:
        with open(filepath, "r") as fd:
            for line, _ in zip(map(str.strip, fd), range(_MAX_SCANNED_LINES)):
                if (match_ := regex.match(line)) is not None:
                    computed_hash = match_.group(1)
                    logging.debug("computed hash: %s", computed_hash)
                    logging.debug("configuration hash: %s", tree.configuration_hash)
                    if bool_ := computed_hash == tree.configuration_hash:
                        logging.warning("%s is up-to-date.", filepath)
                    else:
                        logging.warning("%s is outdated.", filepath)
                    return bool_
    except FileNotFoundError:
        logging.info("%s does not exist.")
    return False


# ############################## Linting-related function #########################################


def run_linter(node: Node) -> None:
    if not node.abs_start_addr < node.abs_end_addr:
        raise MemMapGenerateError(
            f"Address range for region: {node.name}: start address should be lesser than end address",
        )
    for child in node.children:
        if not node.abs_start_addr <= child.abs_start_addr <= node.abs_end_addr:
            raise MemMapGenerateError(
                f"Start address for sub-region: {child.name} is out of bounds of its parent: {node.name}",
            )
        if not node.abs_start_addr <= child.abs_end_addr <= node.abs_end_addr:
            raise MemMapGenerateError(
                f"End address for sub-region: {child.name} is out of bounds of its parent: {node.name}",
            )
        run_linter(child)


# ############################## XML file builder #################################################


class XmlCfgTuple(NamedTuple):
    name: str
    addr: int
    reg_map: Path


class XmlBuilder:
    # match start and end of addrmap{...};
    START_ADDR_MAP_PATTERN = re.compile(r"addrmap\s*{")
    END_ADDR_MAP_PATTERN = re.compile(r"\s*}\s*\w+\s*;")

    def __init__(
        self,
        output_dir: Path,
        source_file: Path,
        ordt_parms_file: Optional[Path] = None,
        render_fn: Optional[RenderFn] = None,
    ) -> None:
        if ordt_parms_file is None:
            if render_fn is None:
                raise ValueError(
                    "'render_fn' should be defined when 'ordt_parms_file' is not."
                )
            ordt_parms_file = output_dir / source_file.with_suffix(".parms").name

        self.rdl_file = output_dir / source_file.with_suffix(".rdl").name
        self.output_file = output_dir / source_file.with_suffix(".xml").name
        self.ordt_parms_file = ordt_parms_file
        self.render_fn = render_fn
        self._tmp_rdl_dir = output_dir / "temp_rdl_files"
        self.unique_node_names: Set[str] = set()

    def to_ordt_valid_name(self, name: str) -> str:
        # Replace all sorts of brackets, dash and space by an underscore
        return "RF_" + re.sub(f"[{re.escape(r'{}[]()- ')}]", "_", name)

    def _get_temp_file(self, name: str, extension: str = ".rdl") -> Path:
        id_ = datetime.now().strftime("%M%S%f")
        return self._tmp_rdl_dir / f"{name}.{id_}{extension}"

    def get_unique_valid_name(self, node: Node) -> str:
        # Avoid ORDT duplicate regfile component error
        assert node.parent is not None, "node should not be root"

        if (
            node.name.upper() in self.unique_node_names
            or len([c for c in node.parent.children if c.name == node.name]) > 1
        ):
            hier_name = f"{node.parent.name} {node.name}"
            logging.warning(
                "Changing duplicate component name: (%s) -> (%s)", node.name, hier_name
            )
            name = hier_name
        else:
            name = node.name

        if name.upper() in self.unique_node_names:
            raise MemMapGenerateError(f"Name '{name}' already used by another region.")

        self.unique_node_names.add(name.upper())
        return self.to_ordt_valid_name(name)

    def create_placeholder_reg_map(self, node: Node) -> XmlCfgTuple:
        assert node.reg_map is None, "node should not have a reg_map"

        name = self.get_unique_valid_name(node)
        rdl = self._get_temp_file(name)

        with open(rdl, "w") as fd:
            fd.write(f"regfile {name} {{\n}};\n")

        return XmlCfgTuple(name, node.abs_start_addr, rdl)

    def process_reg_map(self, node: Node) -> XmlCfgTuple:
        assert node.reg_map is not None, "node should have a reg_map"

        name = self.get_unique_valid_name(node)
        rdl = self._get_temp_file(name)

        with open(node.reg_map, "r") as fd:
            lines = fd.readlines()

        new_lines: List[str] = []

        # look for the start regex from the start of the file
        for i, line in enumerate(lines):
            if self.START_ADDR_MAP_PATTERN.match(line) is not None:
                new_lines.append(f"regfile {name} {{")
                first_idx = i + 1
                break
        else:
            raise RuntimeError(f"Could not find {self.START_ADDR_MAP_PATTERN.pattern}")

        # Look for the end regex from the end of the file
        for i, line in zip(count(start=-1, step=-1), reversed(lines)):
            if self.END_ADDR_MAP_PATTERN.match(line) is not None:
                new_lines.extend(lines[first_idx:i])
                new_lines.append("};\n")
                break
        else:
            raise RuntimeError(f"Could not find {self.END_ADDR_MAP_PATTERN.pattern}")

        with open(rdl, "w") as fd:
            fd.writelines(new_lines)

        return XmlCfgTuple(name, node.abs_start_addr, rdl)

    def get_cfg_tuples(self, node: Node) -> List[XmlCfgTuple]:
        if node.children:
            return list(
                chain.from_iterable(
                    self.get_cfg_tuples(child) for child in node.children
                )
            )

        if node.reg_map is None:
            return [self.create_placeholder_reg_map(node)]

        return [self.process_reg_map(node)]

    def build(self, tree: Node) -> None:
        logging.info("--- Generating XML file.")
        _remove_directory(self._tmp_rdl_dir)
        _create_directory(self._tmp_rdl_dir)

        cfg_tuples = self.get_cfg_tuples(tree)
        logging.debug(NestedStructureLog(cfg_tuples))

        with open(self.rdl_file, "w") as dst:
            with fileinput.input((tup.reg_map for tup in cfg_tuples)) as src:
                dst.writelines(src)
            dst.write("\n")

            dst.write("addrmap {\n")
            for tup in cfg_tuples:
                dst.write(f"\texternal {tup.name} TOP_{tup.name}@{tup.addr};\n")
            dst.write(f"}} {self.rdl_file.with_suffix('').name};")

        if not self.ordt_parms_file.exists():
            assert self.render_fn is not None, "'render_fn' should be defined"
            _ordt_build_parms_file(
                self.ordt_parms_file, tree.abs_start_addr, self.render_fn
            )

        _ordt_generate_xml(self.rdl_file, self.output_file, self.ordt_parms_file)

        logging.info("Generated XML file at %s", self.output_file)


# ############################## Latex file builder ###############################################


class LatexRegionDict(TypedDict):
    name: str
    start_addr: int
    end_addr: int
    size: str
    abs_start_addr: NotRequired[int]
    abs_end_addr: NotRequired[int]
    generated_file: NotRequired[Path]
    regions: NotRequired[List[Self]]


class LatexBuilder:
    TEMPLATE = "memory_map.tex.j2"
    SUBSECTION_NESTING_LMIT = 3
    HASH_REGEX = re.compile(r"% Hash: ([a-zA-Z0-9]+)")

    def __init__(
        self, output_dir: Path, source_file: Path, render_fn: RenderFn
    ) -> None:
        self.output_file = output_dir / source_file.with_suffix(".tex").name
        self.source_file = source_file
        self.render_fn = render_fn
        self._tmp_parms_dir = output_dir / "temp_parms_files"
        self._tmp_tex_dir = output_dir / "temp_tex_files"

    def clear(self, do_not_clear: bool) -> None:
        if do_not_clear:
            return
        _remove_directory(self._tmp_parms_dir)
        _remove_directory(self._tmp_tex_dir)

    @staticmethod
    def get_size(node: Node) -> str:
        # Returns size of address space in bytes/KB/MB/GB
        _size_bytes = (node.end_addr - node.start_addr) + 1
        if _size_bytes < 1024:
            return f"{_size_bytes} bytes"
        if _size_bytes < 1024**2:
            return f"{round(_size_bytes/1024)} KB"
        if _size_bytes < 1024**3:
            return f"{round(_size_bytes/1024 ** 2)} MB"
        return f"{round(_size_bytes/1024 ** 3)} GB"

    def get_regions(self, node: Node) -> LatexRegionDict:
        if node.level >= self.SUBSECTION_NESTING_LMIT:
            raise RecursionError("Latex subsection nesting limit reached.")

        regions: LatexRegionDict = {
            "name": node.name,
            "start_addr": node.start_addr,
            "end_addr": node.end_addr,
            "size": self.get_size(node),
        }

        if node.reg_map is not None:
            regions["abs_start_addr"] = node.abs_start_addr
            regions["abs_end_addr"] = node.abs_end_addr
            regions["generated_file"] = self.generate_texfile(node)

        elif subregions := [self.get_regions(child) for child in node.children]:
            regions["regions"] = subregions

        return regions

    def build(self, tree: Node) -> None:
        logging.info("--- Generating Latex file.")
        self.clear(do_not_clear=False)
        _create_directory(self._tmp_parms_dir)
        _create_directory(self._tmp_tex_dir)

        regions = self.get_regions(tree)
        logging.debug(NestedStructureLog(regions))
        content = self.render_fn(
            template_file=self.TEMPLATE,
            header={
                "filename": self.source_file,
                "hash": tree.configuration_hash,
            },
            root_node=regions,
        )
        with open(self.output_file, "w") as fd:
            fd.write(content)
        logging.info("Generated Latex file at %s", self.output_file)

    def generate_texfile(self, node: Node) -> Path:
        assert node.reg_map is not None, "node should have a reg_map"

        id_ = datetime.now().strftime("%M%S%f")
        output = self._tmp_tex_dir / node.reg_map.with_suffix(f".{id_}.tex").name
        parms = self._tmp_parms_dir / node.reg_map.with_suffix(f".{id_}.parms").name

        _ordt_build_parms_file(parms, node.abs_start_addr, self.render_fn)
        _ordt_generate_latex(node.reg_map, output, parms)
        return output


# ############################## C header file builder ############################################


class CDefineTuple(NamedTuple):
    name: str
    value: int


class CHeaderBuilder:
    TEMPLATE = "memory_map.h.j2"
    HASH_REGEX = re.compile(r"\* @hash ([a-zA-Z0-9]+)")

    def __init__(self, output_file: Path, render_fn: RenderFn) -> None:
        self.output_file = output_file
        self.render_fn = render_fn

    @staticmethod
    def to_valid_name(name: str) -> str:
        # Replace variable inappropriate characters with underscores
        # Add underscore to the beginning if string starts with digit
        return re.sub(r"\W|^(?=\d)", "_", name).upper()

    @classmethod
    def get_name(cls, node: Node) -> str:
        assert node.parent is not None, "node should not be root"

        def _name(node: Node) -> str:
            if node.short_name:
                return cls.to_valid_name(node.short_name)
            return cls.to_valid_name(node.name)

        return f"{_name(node.parent)}_{_name(node)}_BASE_ADDR"

    @classmethod
    def get_defines(cls, node: Node) -> List[List[CDefineTuple]]:
        assert node.children, "node should not be a leaf"
        defs = [
            [
                CDefineTuple(cls.get_name(child), child.abs_start_addr)
                for child in node.children
            ]
        ]
        for child in node.children:
            if child.children:
                defs.extend(cls.get_defines(child))
        return defs

    def build(self, tree: Node) -> None:
        logging.info("--- Generating C header file.")
        defines = self.get_defines(tree)
        logging.debug(NestedStructureLog(defines))
        content = self.render_fn(
            template_file=self.TEMPLATE,
            header={
                "filename": self.output_file,
                "header_name": self.to_valid_name(self.output_file.name),
                "hash": tree.configuration_hash,
            },
            defines=defines,
        )
        with open(self.output_file, "w") as fd:
            fd.write(content.rstrip())
        logging.debug("Generated C header file at %s", self.output_file)


# ############################## Python file builder ##############################################


class _InputField(TypedDict):
    shorttext: str
    lowidx: int
    width: int
    reset: int


class _InputRegister(TypedDict):
    shorttext: str
    baseaddr: int
    field: List[_InputField]


class _InputRegion(TypedDict):
    shorttext: str
    baseaddr: int
    reg: List[_InputRegister]


class InputDict(TypedDict):
    shorttext: str
    regset: List[_InputRegion]


def parse_file(filepath: Path) -> InputDict:
    def _parse_field(node: et.Element) -> _InputField:
        return {
            "shorttext": node.findtext("shorttext", ""),
            "lowidx": int(node.findtext("lowidx", "")),
            "width": int(node.findtext("width", "")),
            "reset": int(node.findtext("reset", "0x00"), base=16),
        }

    def _parse_register(node: et.Element) -> _InputRegister:
        return {
            "shorttext": node.findtext("shorttext", ""),
            "baseaddr": int(node.findtext("baseaddr", ""), base=16),
            "field": [_parse_field(child) for child in node.iter("field")],
        }

    def _parse_region(node: et.Element) -> _InputRegion:
        return {
            "shorttext": node.findtext("shorttext", ""),
            "baseaddr": int(node.findtext("baseaddr", ""), base=16),
            "reg": [_parse_register(child) for child in node.iter("reg")],
        }

    def _parse_root(root: et.Element) -> InputDict:
        return {
            "shorttext": root.findtext("shorttext", ""),
            "regset": [_parse_region(child) for child in root.iter("regset")],
        }

    return _parse_root(et.parse(filepath).getroot())


class _ContextField(TypedDict):
    name: str
    lowidx: int
    width: int
    reset: int


class _ContextRegister(TypedDict):
    name: str
    address: int
    fields: List[_ContextField]


class _ContextRegion(TypedDict):
    name: str
    address: int
    registers: List[_ContextRegister]


class RootDict(TypedDict):
    name: str
    regions: List[_ContextRegion]


def convert(root: InputDict) -> RootDict:

    _STARTS_WITH_NUMBER_REGEX = re.compile(r"\d+.*")

    def _format_name(name: str) -> str:
        if _STARTS_WITH_NUMBER_REGEX.match(new_name := name.split()[0]):
            new_name = f"_{new_name}"
        return new_name.upper()

    def _convert_field(field: _InputField) -> _ContextField:
        return {
            "name": _format_name(field["shorttext"]),
            "lowidx": field["lowidx"],
            "width": field["width"],
            "reset": field["reset"],
        }

    def _convert_register(register: _InputRegister) -> _ContextRegister:
        return {
            "name": _format_name(register["shorttext"]),
            "address": register["baseaddr"],
            "fields": [_convert_field(field) for field in register["field"]],
        }

    def _convert_region(region: _InputRegion) -> _ContextRegion:
        return {
            "name": _format_name(region["shorttext"]),
            "address": region["baseaddr"],
            "registers": [_convert_register(register) for register in region["reg"]],
        }

    def _convert_root(root: InputDict) -> RootDict:
        return {
            "name": _format_name(root["shorttext"]),
            "regions": [_convert_region(region) for region in root["regset"]],
        }

    return _convert_root(root)


class PythonBuilder:
    TEMPLATE = "memory_map.py.j2"
    HASH_REGEX = re.compile(r"# HASH: ([a-zA-Z0-9]+)")

    def __init__(
        self, output_file: Path, input_file: Path, render_fn: RenderFn
    ) -> None:
        self.output_file = output_file
        self.input_file = input_file
        self.render_fn = render_fn

    def build(self, tree: Node) -> None:
        logging.info("--- Generating Python file.")

        logging.info("Processing XML input file.")
        header = {
            "hash": tree.configuration_hash,
        }
        logging.debug(NestedStructureLog(header))

        root = convert(parse_file(self.input_file))
        logging.debug(NestedStructureLog(root))

        logging.info("Rendering template.")
        content = self.render_fn(self.TEMPLATE, header=header, root=root)

        logging.info("Writing output file.")
        with open(self.output_file, "w") as fd:
            fd.write(content)
        logging.debug("Generated Python file at %s", self.output_file)


# ############################## High-level function ##############################################


def ts_render_yaml(
    source_file: Path,
    lint: bool,
    ordt_parms: Optional[Path] = None,
    latex_dir: Optional[Path] = None,
    h_file: Optional[Path] = None,
    py_file: Optional[Path] = None,
    do_not_clear: bool = False,
    force: bool = False,
):

    tree = Node.load_tree(source_file)
    logging.debug(NestedStructureLog(tree))
    print(tree.repr_hierarchy())

    if lint:
        run_linter(tree)

    if (latex_dir, h_file, py_file) == (None, None, None):
        return

    render_fn = create_render_fn()

    if latex_dir is not None:
        lb = LatexBuilder(latex_dir, source_file, render_fn)
        if force or not is_up_to_date(lb.output_file, tree, lb.HASH_REGEX):
            lb.build(tree)
        lb.clear(do_not_clear)

    if h_file is not None:
        if force or not is_up_to_date(h_file, tree, CHeaderBuilder.HASH_REGEX):
            hb = CHeaderBuilder(h_file, render_fn)
            hb.build(tree)

    if py_file is not None:
        if force or not is_up_to_date(py_file, tree, PythonBuilder.HASH_REGEX):
            with TemporaryDirectory() as tmpd:
                xb = XmlBuilder(Path(tmpd), source_file, ordt_parms, render_fn)
                xb.build(tree)
                pb = PythonBuilder(py_file, xb.output_file, render_fn)
                pb.build(tree)
