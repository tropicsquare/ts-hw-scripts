# -*- coding: utf-8 -*-

####################################################################################################
# Functions for generating memory map files.
#
# TODO: License
####################################################################################################

__author__ = "Henri LHote"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Henri LHote"

import fileinput
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from itertools import chain, count
from mmap import mmap
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    List,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    TypedDict,
    Union,
)

import jinja2
import yaml
from typing_extensions import NotRequired, Self

from .ts_grammar import GRAMMAR_MEM_MAP_CONFIG
from .ts_hw_logging import (
    TsColors,
    TsErrCode,
    TsInfoCode,
    TsWarnCode,
    ts_debug,
    ts_info,
    ts_print,
    ts_throw_error,
    ts_warning,
)

TEMPLATE_DIRECTORY = Path(__file__).parent / "jinja_templates"


# TODO fix logging
def info(__msg: str, /) -> None:
    ts_info(TsInfoCode.GENERIC, __msg)


print_in_blue = partial(ts_print, color=TsColors.BLUE)


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
        assert kwargs.get("date") is None, "Key 'date' is reserved."
        return environment.get_template(template_file).render(
            **kwargs, date=datetime.now()
        )

    return _render


class RegionsDict(TypedDict):
    name: str
    short_name: NotRequired[str]
    start_addr: int
    end_addr: int
    reg_map: NotRequired[str]
    regions: NotRequired[Union[List["RegionsDict"], str]]


# TODO remove
def _write_file(filepath: Union[Path, str], content: str) -> None:
    with open(filepath, "w") as fd:
        fd.write(content.rstrip())


def _ordt_run(
    source: Path, output: Path, parms: Path, arg: Literal["xml", "tslatexdoc"]
) -> None:
    command = f"ordt_run.sh -parms {parms} -{arg} {output} {source}"

    info(f"Running ORDT command: {command}")

    completed_process = subprocess.run(
        command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if completed_process.returncode != 0:
        ts_throw_error(TsErrCode.ERR_MMAP_5, completed_process.stderr.decode())

    ts_warning(TsWarnCode.GENERIC, f"Built using ORDT: {output}")


_ordt_generate_xml = partial(_ordt_run, arg="xml")

_ordt_generate_latex = partial(_ordt_run, arg="tslatexdoc")


# TODO keep this?
def is_yaml_file(file: Union[Path, str]) -> bool:
    return Path(file).suffix in (".yml", ".yaml")


# TODO keep this?
def is_xml_file(file: Union[Path, str]) -> bool:
    return Path(file).suffix == ".xml"


# TODO keep this?
def is_rdl_file(file: Union[Path, str]) -> bool:
    return Path(file).suffix == ".rdl"


# TODO keep this?
def is_h_file(file: Union[Path, str]) -> bool:
    return (p := Path(file)).parent.is_dir() and p.suffix == ".h"


def ordt_build_parms_file(
    output_parms_file: Path, base_address: int, render_fn: RenderFn
) -> None:
    """builds a parameters file with default parameters for ordt in the output directory"""
    _write_file(
        output_parms_file,
        render_fn("parms_file.parms.j2", top={"base_address": base_address}),
    )


# TODO move to argparser
def unpack_env_var_path(path: str) -> str:
    """Unpacks environment variables in path."""
    unpacked_path = os.path.expandvars(path)
    if "$" in path and unpacked_path == path:
        ts_throw_error(TsErrCode.ERR_MMAP_7, path)
    return unpacked_path


def load_yaml(filepath: Union[Path, str]) -> RegionsDict:
    filepath = unpack_env_var_path(str(filepath))
    assert is_yaml_file(filepath)

    ts_debug(f"Opening YAML file: {filepath}")
    with open(filepath) as fd:
        content = yaml.safe_load(fd)

    GRAMMAR_MEM_MAP_CONFIG.validate(content)  # type: ignore
    return content


def render_yaml_parent(
    top_level_filepath: Path,
    lint: bool,
    ordt_parms_file: Optional[Path] = None,
    latex_dir: Optional[Path] = None,
    xml_dir: Optional[Path] = None,
    c_header_file: Optional[Path] = None,
    do_not_clear: object = 0,
):
    tree = Node.load_tree(Path(top_level_filepath))
    ts_debug(tree)
    ts_print(tree.pretty_repr())

    ts_info(TsInfoCode.INFO_MMAP_0, tree.start_addr, tree.end_addr)

    if lint:
        run_linter(tree)

    if (latex_dir, xml_dir, c_header_file) == (None, None, None):
        return

    render_fn = create_render_fn()

    if latex_dir is not None:
        b = LatexBuilder(latex_dir, top_level_filepath, render_fn)
        b.build(tree)
        b.clear(do_not_clear)

    if xml_dir is not None:
        r = XmlBuilder(xml_dir, top_level_filepath, ordt_parms_file, render_fn)
        r.build(tree)
        r.clear(do_not_clear)

    if c_header_file is not None:
        h = CHeaderBuilder(c_header_file, render_fn)
        h.build(tree)


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
            print_in_blue(" -> ".join(reversed(error_path)))
            raise RecursionError(
                f"Nesting {level} exceeds limit of {cls.MAX_NESTING_LEVEL}"
            )

        if (reg_map := cfg.get("reg_map")) is not None:
            assert cfg.get("regions") is None
            assert is_rdl_file(reg_map)
            ts_debug(f"Including RDL file: {reg_map}")
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
            filepath = source.parent / regions
            cfg = load_yaml(filepath)
            assert cfg.get("reg_map") is None
            return cls._load_regions(cfg.get("regions", []), filepath, level, parent)

        # TODO add some verbosity
        return [cls.new(region, source, level, parent) for region in regions]

    @classmethod
    def load_tree(cls, filepath: Path) -> Self:
        return cls.new(load_yaml(filepath), filepath)

    # TODO remove
    def is_leaf(self) -> bool:
        return not self.children

    # TODO remove
    def has_reg_map(self) -> bool:
        return self.reg_map is not None

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

    def pretty_repr(self) -> str:
        l = ["{}[L{}] {}".format("\t" * self.level, self.level, self.name)]
        l.extend(child.pretty_repr() for child in self.children)
        return "\n".join(l)


def run_linter(tree: Node) -> None:
    for child in tree.children:
        if not tree.abs_start_addr <= child.abs_start_addr <= tree.abs_end_addr:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"Start address for sub-region: {child.name} is out of bounds of its parent: {tree.name}",
            )
        if not tree.abs_start_addr <= child.abs_end_addr <= tree.abs_end_addr:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"End address for sub-region: {child.name} is out of bounds of its parent: {tree.name}",
            )
        run_linter(child)


# TODO rework
def _remove_directory(dirpath: Path, build_type: Optional[str] = None) -> None:
    if build_type is None:
        build_type = ""
    else:
        build_type = f" {build_type}"
    print_in_blue(f"Removing temporary{build_type} files directory: {dirpath}")
    shutil.rmtree(dirpath, ignore_errors=True)
    ts_debug("Done.")


# TODO rework
def _create_directory(dirpath: Path, build_type: Optional[str] = None) -> None:
    if build_type is None:
        build_type = ""
    else:
        build_type = f" {build_type}"
    print_in_blue(f"Removing temporary{build_type} files directory: {dirpath}")
    dirpath.mkdir(parents=True, exist_ok=True)
    ts_debug("Done.")


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
            ordt_parms_file = output_dir / source_file.with_suffix(".parms").name
            if render_fn is None:
                raise ValueError(
                    "'render_fn' should be defined when 'ordt_parms_file' is not."
                )

        self.rdl_file = output_dir / source_file.with_suffix(".rdl").name
        self.output_file = output_dir / source_file.with_suffix(".xml").name
        self.ordt_parms_file = ordt_parms_file
        self.render_fn = render_fn

        self._tmp_rdl_dir = output_dir / "temp_rdl_files"

        _remove_directory(output_dir)
        _create_directory(self._tmp_rdl_dir)

        # TODO assess usefulness
        # avoid ORDT duplicate regfile component error
        # note: ORDT cares only about exact duplicates, case is irrelevant
        self.unique_node_names: Set[str] = set()

    def clear(self, do_not_clear: object):
        if do_not_clear:
            return
        _remove_directory(self._tmp_rdl_dir, "RDL")

    def to_ordt_valid_name(self, name: str) -> str:
        # Replace all sorts of brackets, dash and space by an underscore
        return "RF_" + re.sub(f"[{re.escape(r'{}[]()- ')}]", "_", name)

    def _get_temp_file(self, name: str, extension: str = ".rdl") -> Path:
        id_ = datetime.now().strftime("%M%S%f")
        return self._tmp_rdl_dir / f"{name}.{id_}{extension}"

    # TODO remove if needed - see __init__ method
    def get_unique_valid_name(self, node: Node) -> str:
        if node.name.upper() not in self.unique_node_names:
            name = self.to_ordt_valid_name(node.name)

        else:
            assert node.parent is not None
            hier_name = f"{node.parent.name} {node.name}"
            print_in_blue(
                f"Changing duplicate component name: ({node.name}) -> ({hier_name})"
            )
            name = self.to_ordt_valid_name(f"{node.parent.name} {node.name}")

        self.unique_node_names.add(node.name.upper())
        return name

    def create_placeholder_reg_map(self, node: Node) -> XmlCfgTuple:
        assert node.reg_map is None

        name = self.get_unique_valid_name(node)
        rdl = self._get_temp_file(name)

        with open(rdl, "w") as fd:
            fd.write(f"regfile {name} {{\n}};\n")

        return XmlCfgTuple(name, node.abs_start_addr, rdl)

    def process_reg_map(self, node: Node) -> XmlCfgTuple:
        assert node.reg_map is not None

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
        cfg_tuples = self.get_cfg_tuples(tree)
        ts_debug(cfg_tuples)

        with open(self.rdl_file, "w") as dst:
            with fileinput.input((tup.reg_map for tup in cfg_tuples)) as src:
                dst.writelines(src)
            dst.write("\n")

            dst.write("addrmap {\n")
            for tup in cfg_tuples:
                dst.write(f"\texternal {tup.name} TOP_{tup.name}@{tup.addr};\n")
            dst.write(f"}} {self.rdl_file.with_suffix('').name};")

        _ordt_generate_xml(self.rdl_file, self.output_file, self.ordt_parms_file)

        print_in_blue(f"Generated XML file at {self.output_file}")


class LatexRegionDict(TypedDict):
    name: str
    start_addr: int
    end_addr: int
    size: str
    abs_start_addr: NotRequired[int]
    abs_end_addr: NotRequired[int]
    generated_file: NotRequired[Path]
    regions: NotRequired[List["LatexRegionDict"]]


class LatexBuilder:
    TEMPLATE = "memory_map.tex.j2"
    SUBSECTION_NESTING_LMIT = 3

    def __init__(
        self, output_dir: Path, source_file: Path, render_fn: RenderFn
    ) -> None:
        self.output_file = output_dir / source_file.with_suffix(".tex").name
        self.source_file = source_file
        self.render_fn = render_fn

        self._tmp_parms_dir = output_dir / "temp_parms_files"
        self._tmp_tex_dir = output_dir / "temp_tex_files"

        _remove_directory(output_dir)
        _create_directory(self._tmp_parms_dir)
        _create_directory(self._tmp_tex_dir)

    def clear(self, do_not_clear: object) -> None:
        if do_not_clear:
            return
        _remove_directory(self._tmp_parms_dir, "PARMS")
        _remove_directory(self._tmp_tex_dir, "TEX")

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
        regions = self.get_regions(tree)
        ts_debug(regions)
        _write_file(
            self.output_file,
            self.render_fn(
                template_file=self.TEMPLATE,
                header={
                    "filename": self.source_file,
                },
                root_node=regions,
            ),
        )
        print_in_blue(f"Generated Latex file at {self.output_file}")

    def generate_texfile(self, node: Node) -> Path:
        assert node.reg_map is not None

        id_ = datetime.now().strftime("%M%S%f")
        output = self._tmp_tex_dir / node.reg_map.with_suffix(f".{id_}.tex").name
        parms = self._tmp_parms_dir / node.reg_map.with_suffix(f".{id_}.parms").name

        ordt_build_parms_file(parms, node.abs_start_addr, self.render_fn)
        _ordt_generate_latex(node.reg_map, output, parms)
        return output


class CDefineTuple(NamedTuple):
    name: str
    value: int


class CHeaderBuilder:
    TEMPLATE = "memory_map.h.j2"

    def __init__(self, output_file: Path, render_fn: RenderFn) -> None:
        self.output_file = output_file
        self.render_fn = render_fn

    @staticmethod
    def to_valid_c_define_name(name: str) -> str:
        # Replace variable inappropriate characters with underscores
        # Add underscore to the beginning if string starts with digit
        return re.sub(r"\W|^(?=\d)", "_", name).upper()

    @classmethod
    def get_name(cls, node: Node) -> str:
        assert node.parent is not None

        def _name(node: Node) -> str:
            if node.short_name:
                return cls.to_valid_c_define_name(node.short_name)
            return cls.to_valid_c_define_name(node.name)

        return f"{_name(node.parent)}_{_name(node)}_BASE_ADDR"

    @classmethod
    def get_defines(cls, node: Node) -> List[List[CDefineTuple]]:
        assert node.children
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
        defines = self.get_defines(tree)
        ts_debug(defines)
        _write_file(
            self.output_file,
            self.render_fn(
                template_file=self.TEMPLATE,
                header={
                    "filename": self.output_file,
                    "header_name": self.to_valid_c_define_name(self.output_file.name),
                },
                defines=defines,
            ),
        )
        print_in_blue(f"Generated header file at {self.output_file}")
