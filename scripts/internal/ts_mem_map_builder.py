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

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
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


# TODO keep this?
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
        render_fn(
            "parms_file.parms.j2", header={}, body={"base_address": base_address}
        ),
    )


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


# TODO use Path everywhere
def render_yaml_parent(
    top_level_filepath: str,
    lint: bool,
    ordt_parms_file: str,
    latex_dir: Optional[str] = None,
    xml_dir: Optional[str] = None,
    c_header_file: Optional[str] = None,
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
        b = LatexBuilder(Path(latex_dir), Path(top_level_filepath), render_fn)
        b.build(tree)
        b.clear(do_not_clear)

    if xml_dir is not None:
        r = XmlBuilder(xml_dir, top_level_filepath, ordt_parms_file)
        r.build_output(tree)
        r.clear(do_not_clear)

    if c_header_file is not None:
        h = CHeaderBuilder(Path(c_header_file), render_fn)
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
            error_path = [node.name] + [p.name for p in node.parents()]
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

    def parents(self) -> List[Self]:
        if self.parent is None:
            return []
        return [self.parent] + self.parent.parents()

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


def _remove_directory(dirpath: Path, build_type: Optional[str] = None) -> None:
    if build_type is None:
        build_type = ""
    else:
        build_type = f" {build_type}"
    print_in_blue(f"Removing temporary{build_type} files directory: {dirpath}")
    shutil.rmtree(dirpath, ignore_errors=True)
    ts_debug("Done.")


def _create_directory(dirpath: Path, build_type: Optional[str] = None) -> None:
    if build_type is None:
        build_type = ""
    else:
        build_type = f" {build_type}"
    print_in_blue(f"Removing temporary{build_type} files directory: {dirpath}")
    dirpath.mkdir(parents=True, exist_ok=True)
    ts_debug("Done.")


class XmlBuilder:
    def __init__(
        self, output_dir: str, source_file: str, ordt_parms_file: Optional[str]
    ) -> None:
        self.output_dir = Path(output_dir)
        main_filename = Path(source_file).stem

        self.temp_rdl_files_path = self.output_dir / "temp_rdl_files"
        self.temp_rdl_files_path.mkdir(exist_ok=True)

        self.rdl_path = self.output_dir / f"{main_filename}.rdl"
        self.rdl_path.touch()

        self.xml_path = self.output_dir / f"{main_filename}.xml"

        self.ordt_parms_path = ordt_parms_file
        self.rdl_list: List[Node] = []

    def clear(self, do_not_clear: object):
        if do_not_clear:
            return
        _remove_directory(self.temp_rdl_files_path, "RDL")

    def ordt_valid_identifier(self, name: str) -> str:
        """(very naive) If string is not a valid ORDT identifier name, convert it to one."""
        return re.sub(f"[{re.escape(r'{}[]()-_ ')}]", "_", name)

    def build_output(self, tree: Node):
        self.walk_tree(tree)

        # match start and end of addrmap{...};
        startAddrMapPattern = re.compile(r"addrmap\s*{")
        endAddrMapPattern = re.compile(r"\s*}\s*\w+\s*;")

        addrMap_str = "\naddrmap { "

        with open(self.rdl_path, "w") as output_file:
            rdl_dupes_list = [rdl.name for rdl in self.rdl_list]

            for rdl in self.rdl_list:
                with open(rdl.reg_map, "r") as rf:
                    lines = rf.readlines()

                # search for start and end of addrmap element
                start_index = next(
                    (
                        index
                        for index, line in enumerate(lines)
                        if startAddrMapPattern.match(line)
                    ),
                    0,
                )
                end_index = next(
                    (
                        index
                        for index, line in reversed(list(enumerate(lines)))
                        if endAddrMapPattern.match(line)
                    ),
                    -1,
                )

                # avoid ORDT duplicate regfile component error
                # note: ORDT cares only about exact duplicates, case is irrelevant
                if rdl_dupes_list.count(rdl.name) > 1:
                    rf_name = f"{rdl.parent.name} {rdl.name}"
                    print_in_blue(
                        f"Changing duplicate component name: ({rdl.name}) -> ({rf_name})"
                    )
                else:
                    rf_name = rdl.name
                    rdl_dupes_list.append(rdl.name)

                rf_name = f"RF_{self.ordt_valid_identifier(rf_name)}"

                lines[start_index] = f"regfile {rf_name} {{"
                lines[end_index] = "};"

                output_file.writelines(lines[start_index : end_index + 1])

                # addrmap string instantiates all regfile objects with start addresses
                addrMap_str += "\n\texternal {0} TOP_{0}@{1};".format(
                    rf_name, rdl.abs_start_addr
                )
                output_file.write("\n")

            # use output rdl file name as addrmap name
            addrMap_str += (
                f"\n}} {self.ordt_valid_identifier(Path(self.rdl_path).stem)};"
            )
            output_file.write(addrMap_str)

        _ordt_generate_xml(
            source=self.rdl_path, output=self.xml_path, parms=self.ordt_parms_path
        )

    def walk_tree(self, tree: Node) -> None:
        for child in tree.children:
            # ignore parent nodes

            if child.is_leaf():
                if not child.has_reg_map():
                    self.make_empty_region_rdl(child)
                self.rdl_list.append(child)

            self.walk_tree(child)

    def make_empty_region_rdl(self, node: Node):
        # output directory is always relative to where script is running
        temp_empty_rdl = (
            self.temp_rdl_files_path / f"{self.ordt_valid_identifier(node.name)}.rdl"
        )

        with open(temp_empty_rdl, "w") as fd:
            fd.write(f"addrmap{{\n\n}} {self.ordt_valid_identifier(node.name)};")

        node.reg_map = str(temp_empty_rdl)


class LatexRegionsDict(TypedDict):
    name: str
    start_addr: int
    end_addr: int
    size: str
    abs_start_addr: NotRequired[int]
    abs_end_addr: NotRequired[int]
    generated_file: NotRequired[Path]
    regions: NotRequired[List["LatexRegionsDict"]]


class LatexBuilder:
    TEMPLATE = "memory_map.tex.j2"
    SUBSECTION_NESTING_LMIT = 3

    def __init__(
        self, output_dir: Path, source_file: Path, render_fn: RenderFn
    ) -> None:
        self.output_file = output_dir / source_file.with_suffix(".tex").name

        self._tmp_parms_dir = output_dir / "temp_parms_files"
        self._tmp_tex_dir = output_dir / "temp_tex_files"

        _remove_directory(output_dir)
        _create_directory(self._tmp_parms_dir)
        _create_directory(self._tmp_tex_dir)

        self.source_file = source_file
        self.render_fn = render_fn

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

    def get_regions(self, node: Node) -> LatexRegionsDict:
        if node.level >= self.SUBSECTION_NESTING_LMIT:
            raise RecursionError("Latex subsection nesting limit reached.")

        regions: LatexRegionsDict = {
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


class CHeaderBuilder:
    TEMPLATE = "memory_map.h.j2"

    def __init__(self, output_file: Path, render_fn: RenderFn) -> None:
        self.output_file = output_file
        self.render_fn = render_fn

    @staticmethod
    def format_to_valid_c_def(name: str) -> str:
        # Replaces variable inappropriate characters with underscores
        # Adds underscore to beginning if string starts with digit
        return re.sub(r"\W|^(?=\d)", "_", name).upper()

    @classmethod
    def get_name(cls, node: Node) -> str:
        assert node.parent is not None

        def _name(node: Node) -> str:
            if node.short_name:
                return cls.format_to_valid_c_def(node.short_name)
            return cls.format_to_valid_c_def(node.name)

        return f"{_name(node.parent)}_{_name(node)}_BASE_ADDR"

    @classmethod
    def get_defines(cls, node: Node) -> List[List[Tuple[str, int]]]:
        assert node.children
        defs = [
            [(cls.get_name(child), child.abs_start_addr) for child in node.children]
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
                    "header_name": self.format_to_valid_c_def(self.output_file.name),
                },
                defines=defines,
            ),
        )
        print_in_blue(f"Generated header file at {self.output_file}")
