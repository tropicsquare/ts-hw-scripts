import os
import re
import yaml
import typing
from pathlib import Path
from textwrap import dedent
from pprint import pprint
import subprocess
from dataclasses import dataclass, field
from schema import Schema, And, SchemaError, Optional

from .ts_hw_logging import *
from .ts_hw_common import *
from .ts_grammar import *

current_level = []

def pretty_hex(num: int):
    """force print 8 hex digits, add space in between"""

    tmp = hex(num).upper()
    tmp = tmp[2:].zfill(8)
    tmp = "0x" + tmp[:4] + " " + tmp[4:]

    return tmp


def write_line(file, line):
    with open(file, "a") as f:
        f.write(line)


def ordt_run(source, output, parms):
    if Path(output).suffix == ".xml":
        command = f"ordt_run.sh -parms {parms} -xml {output} {source}"
    else:
        command = f"ordt_run.sh -parms {parms} -tslatexdoc {output} {source}"

    ts_info(TsInfoCode.GENERIC, f"Running ORTDT command: {command}")

    process = subprocess.Popen(
        command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    std_out, std_err = process.communicate()

    if process.returncode != 0:
        ts_throw_error(TsErrCode.ERR_MMAP_5, str(std_err, encoding="utf-8"))

    ts_warning(TsWarnCode.GENERIC, f"Built using ORDT: {Path(output)}")


def is_yaml_file(file: str):
    if Path(file).suffix in [".yml", ".yaml"]:
        return True
    else:
        ts_throw_error(TsErrCode.ERR_MMAP_2, os.path.basename(file))


def is_rdl_file(file: str):
    if Path(file).suffix == ".rdl":
        return True
    else:
        ts_throw_error(TsErrCode.ERR_MMAP_3, os.path.basename(file))


def latex_valid_identifier(name):
    """(very naive) If string is not a valid latex identifier name, convert it to one."""
    name = name.replace("{", "_").replace("}", "_")
    return name


def ordt_build_parms_file(output_dir, ordt_parms_filename, base_address=0):
    """builds a parameters file with default parameters for ordt in the output directory"""

    default_parms = dedent(
        f"""\
        global {{
            base_address = {base_address}
        }}
        // rdl input parameters
        input rdl {{
            resolve_reg_category    = true      // if register category is unspecified, try to determine from rdl
            lint_rdl                = false
        }}

        // Latex output parameters
        output tslatexdoc {{
            add_latex_preamble      = false     // Add LaTex pre-amble (stand-alone document)
            add_latex_reg_summary   = true      // Add register summary table on top
            add_landscape_tables    = true	    // Add register table in landscape mode
            add_absolute_addresses  = true      // Sums up absolute address from parameters to offsets
        }}
    """
    )

    with open(os.path.join(output_dir, ordt_parms_filename), "w") as fp:
        fp.write(default_parms)

    return os.path.join(output_dir, ordt_parms_filename)


def load_rdl(target_filepath: str, current_level: typing.Optional[str] = None):
    
    current_dir = Path(current_level).parent
    
    target = current_dir.joinpath(Path(target_filepath))
    
    if not target.exists():
        ts_throw_error(TsErrCode.ERR_MMAP_4, target)

    return target


def load_yaml(target_filepath: str, current_level: typing.Optional[str] = None):

    if current_level is None:
        current_dir = Path(target_filepath).parent
        target_filepath = current_dir.joinpath(Path(target_filepath).name)
    else:
        current_dir = Path(current_level).parent
        target_filepath = current_dir.joinpath(Path(target_filepath))
    try:
        with open(target_filepath) as ft:
            return yaml.safe_load(ft), target_filepath
    except FileNotFoundError:
        ts_throw_error(TsErrCode.ERR_MMAP_4, target_filepath)


def render_yaml_parent(
    ordt_parms_file, top_level_filepath, lint:bool, latex_dir=None, xml_dir=None
):

    rendered_yaml, tmp_current_level = load_yaml(top_level_filepath, current_level=None)
    current_level.append(tmp_current_level)

    ts_warning(TsWarnCode.WARN_MMAP_1, rendered_yaml["name"])

    ts_info(
        TsInfoCode.INFO_MMAP_0,
        pretty_hex(rendered_yaml["start_addr"]),
        pretty_hex(rendered_yaml["end_addr"]),
    )

    GRAMMAR_MEM_MAP_CONFIG.validate(rendered_yaml)

    tree = Node.load_regions(rendered_yaml)

    if lint is True: 
        l = linter()
        l.lint(tree)
        
    if latex_dir is not None:
        b = latex_builder(latex_dir, top_level_filepath, ordt_parms_file)
        b.build_output(tree)

    if xml_dir is not None:
        r = xml_builder(xml_dir, top_level_filepath, ordt_parms_file)
        r.build_output(tree)

    tree.draw()


@dataclass
class Node:
    name: str
    start_addr: int
    end_addr: int
    reg_map: str = ""
    parent: "Node" = field(init=False, default=None)
    children: typing.List["Node"] = field(init=False, default_factory=list)

    nesting_level: typing.ClassVar[int] = 0
    MAX_NESTING_LEVEL: typing.ClassVar[int] = 5

    recursion_error_list: typing.ClassVar[list] = []

    def draw(self, level=0):
        ts_print("{}[L{}] {}".format("\t" * level, self.get_nesting_level(), self.name))
        for child in self.children:
            child.draw(level=level + 1)

    def get_nesting_level(self):
        temp = self.parent
        count = 0
        while temp != None:
            count += 1
            temp = temp.parent
        return count

    @classmethod
    def load_regions(cls, top: dict) -> "Node":
        cls.nesting_level += 1
        cls.recursion_error_list.append(top["name"] + " ->")

        if cls.nesting_level > cls.MAX_NESTING_LEVEL:
            ts_print(*cls.recursion_error_list, color=TsColors.BLUE)
            raise RecursionError(f"Nesting level: {cls.nesting_level} exceeds limit of {cls.MAX_NESTING_LEVEL}")

        if "regions" in top and top["regions"] is not None:
            top_node = cls(
                name=top["name"],
                start_addr=top["start_addr"],
                end_addr=top["end_addr"],
                reg_map=top.get("reg_map", ""),
            )

            # force validate all immediate child nodes
            for region in top["regions"]:
                ts_debug(f"currently validating: {region['name']}")
                GRAMMAR_MEM_MAP_CONFIG.validate(region)

            for region in top["regions"]:
                ts_warning(TsWarnCode.WARN_MMAP_0, region["name"])
                ts_info(
                    TsInfoCode.INFO_MMAP_0,
                    pretty_hex(region["start_addr"]),
                    pretty_hex(region["end_addr"]),
                )

                # node has no children
                if "reg_map" in region and is_rdl_file(region["reg_map"]):
                    ts_debug("Including RDL file: {}".format(region["reg_map"]))
                    region["reg_map"] = load_rdl(region["reg_map"], current_level[-1])

                    temp_child = cls(
                        name=region["name"],
                        start_addr=region["start_addr"],
                        end_addr=region["end_addr"],
                        reg_map=region["reg_map"],
                    )
                    temp_child.parent = top_node
                    top_node.children.append(temp_child)

                elif "regions" in region:

                    if isinstance(region["regions"], str) and is_yaml_file(region["regions"]):
                        ts_debug("Opening YAML file: {}".format(region["regions"]))

                        temp_yaml, temp_current_level = load_yaml(
                            region["regions"], current_level[-1]
                        )

                        current_level.append(temp_current_level)

                        child_node = cls.load_regions(temp_yaml)
                        
                        current_level.pop()

                        # overwrite from same node in parent file
                        child_node.name = region["name"]
                        child_node.start_addr = region["start_addr"]
                        child_node.end_addr = region["end_addr"]

                    elif isinstance(region["regions"], list):
                        child_node = cls.load_regions(region)

                    child_node.parent = top_node
                    top_node.children.append(child_node)
                # node is an empty memory region with no children
                elif "regions" not in region and "reg_map" not in region:
                    temp_child = cls(
                        name=region["name"],
                        start_addr=region["start_addr"],
                        end_addr=region["end_addr"],
                    )

                    temp_child.parent = top_node
                    top_node.children.append(temp_child)

            cls.nesting_level -= 1

        else:
            ts_throw_error(TsErrCode.ERR_MMAP_1, current_level[-1])

        return top_node


class linter: 
    def absolute_start_addr(self, node):
        temp = node.parent
        addr = node.start_addr
        while temp != None:
            addr += temp.start_addr
            temp = temp.parent
        return addr        

    def absolute_end_addr(self, node):
        temp = node.parent
        addr = node.end_addr
        while temp != None:
            addr += temp.start_addr
            temp = temp.parent
        return addr

    def lint(self, tree):
        for child in tree.children:
            
            if not self.absolute_start_addr(tree) <= self.absolute_start_addr(child) <= self.absolute_end_addr(tree):
                ts_throw_error(TsErrCode.GENERIC, f"Start address for sub-region: {child.name} is out of bounds of its parent: {tree.name}")

            if not self.absolute_start_addr(tree) <= self.absolute_end_addr(child) <= self.absolute_end_addr(tree):
                ts_throw_error(TsErrCode.GENERIC, f"End address for sub-region: {child.name} is out of bounds of its parent: {tree.name}")
            
            self.lint(child)

class xml_builder:
    def __init__(self, output_dir, source_file, ordt_parms_file):
        self.output_dir = Path(output_dir)
        main_filename = Path(source_file).stem
        
        self.temp_rdl_files_path = self.output_dir / 'temp_rdl_files'
        self.temp_rdl_files_path.mkdir(exist_ok=True)

        self.rdl_path = self.output_dir / f"{main_filename}.rdl"
        self.rdl_path.touch()

        self.xml_path = self.output_dir / f"{main_filename}.xml"

        self.ordt_parms_path = ordt_parms_file
        self.rdl_list = []

    def is_leaf(self, node):
        if len(node.children) == 0 and node.reg_map != "":
            return True           
        else:
            return False

    def is_empty_region(self, node):
        if len(node.children) == 0 and node.reg_map == "":
            return True
        else: 
            return False

    def get_absolute_addr(self, node):
        temp = node.parent
        addr = node.start_addr
        while temp != None:
            addr += temp.start_addr
            temp = temp.parent
        return addr

    def ordt_valid_identifier(self, name):
        """(very naive) If string is not a valid ORDT identifier name, convert it to one."""
        name = name.replace("{", "_").replace("}", "_")
        name = name.replace("[", "_").replace("]", "_")
        name = name.replace("(", "_").replace(")", "_")
        name = name.replace("-", "_")
        name = name.replace(" ", "_")
        return name

    def build_output(self, tree):
        self.walk_tree(tree)

        # match start and end of addrmap{...};
        startAddrMapPattern = re.compile(r"addrmap\s*{")
        endAddrMapPattern = re.compile(r"\s*}\s*\w+\s*;")

        addrMap_str = "\naddrmap { "

        with open(self.rdl_path, "w") as output_file:

            for rdl in self.rdl_list:

                with open(rdl.reg_map, "r") as rf:
                    lines = rf.readlines()

                start_index = 0
                end_index = -1

                # search for start of addrmap element
                for index, line in enumerate(lines):
                    if startAddrMapPattern.match(line):
                        start_index = index
                        break
                # search for end of addrmap element
                for index, line in reversed(list(enumerate(lines))):
                    if endAddrMapPattern.match(line):
                        end_index = index
                        break

                rdl.name = "RF_"+self.ordt_valid_identifier(rdl.name)

                lines[start_index] = f"regfile {rdl.name} {{"
                lines[end_index] = "};"

                output_file.writelines(lines[start_index : end_index + 1])

                # addrmap string instantiates all regfile objects with start addresses
                addrMap_str += "\n\texternal {0} TOP_{0}@{1};".format(
                    rdl.name, self.get_absolute_addr(rdl)
                )
                output_file.write("\n")

            # use output rdl file name as addrmap name
            addrMap_str += f"\n}} {self.ordt_valid_identifier(Path(self.rdl_path).stem)};"
            output_file.write(addrMap_str)

        ordt_run(source=self.rdl_path, output=self.xml_path, parms=self.ordt_parms_path)

    def walk_tree(self, tree):
        for child in tree.children:
            # ignore parent nodes
            if self.is_leaf(child):
                self.rdl_list.append(child)

            elif self.is_empty_region(child):
                self.make_empty_region_rdl(child)
                self.rdl_list.append(child)

            self.walk_tree(child)

    def make_empty_region_rdl (self, node):
        
        # output directory is always relative to where script is running
        temp_empty_rdl = self.temp_rdl_files_path/ f'{self.ordt_valid_identifier(node.name)}.rdl'
 
        with open(temp_empty_rdl, 'w') as fr: 
            fr.write(f"addrmap{{\n\n}} {self.ordt_valid_identifier(node.name)};")

        node.reg_map = str(temp_empty_rdl)
       

class latex_builder:
    def __init__(self, output_dir, source_file, ordt_parms_file):
        self.output_dir = Path(output_dir)
        main_filename = Path(source_file).stem

        self.latex_path = Path(output_dir) / f"{main_filename}.tex"
        self.latex_path.touch()
        open(self.latex_path, "w").close()

        self.ordt_parms_path = ordt_parms_file

    def get_nesting_level(self, node):
        temp = node.parent
        count = 0
        while temp != None:
            count += 1
            temp = temp.parent
        return count

    def get_absolute_addr(self, node):
        temp = node.parent
        addr = node.start_addr
        while temp != None:
            addr += temp.start_addr
            temp = temp.parent
        return addr

    def is_leaf(self, node):
        if len(node.children) == 0:
            # naive assumption b/c node was already validated in class Node
            if node.reg_map != "":
                return "rdl"

            else:
                return "empty"

    def build_output(self, tree):
        self.add_subregion_table(tree)
        self.walk_tree(tree)

    def walk_tree(self, tree):
        for child in tree.children:
            if self.is_leaf(child) == "rdl":
                self.add_texfile(child)
            elif self.is_leaf(child) == "empty":
                pass
            else:
                self.add_subregion_table(child)
                self.walk_tree(child)

    def add_texfile(self, node):
        tmp_output = f"{Path(node.reg_map).stem}.tex"
        tmp_parms = f"{Path(node.reg_map).stem}.parms"

        ordt_build_parms_file(
            output_dir=self.output_dir,
            ordt_parms_filename=tmp_parms,
            base_address=hex(self.get_absolute_addr(node)),
        )

        ordt_run(
            source=node.reg_map,
            output=self.output_dir / tmp_output,
            parms=self.output_dir / tmp_parms,
        )

        self.add_subsection(node)

        # copy entire file instead of including
        tmp_file = open(self.output_dir / tmp_output, "r")
        write_line(self.latex_path, tmp_file.read())
        tmp_file.close()

    def add_subregion_table(self, node):

        self.add_subsection(node)

        write_line(self.latex_path, latex_content.subregion_table_start())

        for child in node.children:
            write_line(
                self.latex_path,
                latex_content.subregion_table_row(
                    latex_valid_identifier(child.name),
                    pretty_hex(child.start_addr),
                    pretty_hex(child.end_addr),
                ),
            )

        write_line(self.latex_path, latex_content.subregion_table_end())

    def add_comment(self, comment=""):
        write_line(self.latex_path, latex_content.comment(comment))

    def add_subsection(self, node):
        """add LaTeX section/subsection/subsubsection based on nesting level"""

        nesting_level = self.get_nesting_level(node)

        # 0 -> section, 1 -> subsection, 1 -> subsubsection,
        if nesting_level >= 3:
            raise RecursionError("Latex subsection nesting limit reached.")

        self.add_comment(node.name)
        write_line(
            self.latex_path,
            latex_content.section_start(
                nesting_level,
                latex_valid_identifier(node.name),
                pretty_hex(node.start_addr),
            ),
        )


class latex_content(LogEnum):

    section_start = [
        lambda nesting_level, block_name, start_addr: dedent(
            rf"""
        \pagebreak
        \Ts{'Sub'*nesting_level}Section {{{block_name}}}

        \textbf{{Base Address:}} {{{start_addr}}}
        \vspace{{4mm}}
        """
        )
    ]

    comment = [lambda comment="": dedent(f"\n{'%'*69}\n% {comment}\n{'%'*69}")]

    subregion_table_start = [
        lambda: dedent(
            r"""
        \begin{TropicRatioTable2Col}
        {0.5}                                         {0.5}
        {Memory region                                & Address offset range}
        """
        )
    ]

    subregion_table_row = [
        lambda block_name, start_addr, end_addr: rf"""
        \multirow {{2}} {{*}} {{{block_name}}}             & {start_addr}     \\
                                                    & {end_addr}     \Ttlb%
        """
    ]

    subregion_table_end = [lambda: dedent("\n\end{TropicRatioTable2Col}\n")]
