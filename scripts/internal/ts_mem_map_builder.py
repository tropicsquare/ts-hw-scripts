import os
import re
import yaml
import typing
from pathlib import Path
from textwrap import dedent
from pprint import pprint
import subprocess

from schema import Schema, And, SchemaError, Optional
from .ts_hw_logging import *
from .ts_hw_common import *
from .ts_grammar import *

""" rules
#. Every element needs either regions or reg_map [RESOLVED]
#. Only one regions per level [TODO]
#. Only one top level element per file [TODO]
#. reg_map and regions can't exist together in the same element [RESOLVED]
#. Warn if no rdlfile doesn't exist or no rdl file defined in deepest level element [RESOLVED]
#. Address range overlaps [TODO]
"""

# List of all nodes with a 'reg_map' key
rdl_list = []
current_level = []

def __ordt_run(source, output, parms):
    xml_command = f"ordt_run.sh -parms {parms} -xml {output} {source}"

    try:
        subprocess.check_output(xml_command.split())
    except subprocess.CalledProcessError as e:
        ts_throw_error(TsErrCode.ERR_MMAP_5, str(e.stdout, encoding='utf-8'))

    ts_print(f'Generated XML file: {output}', color=TsColors.GREEN)

def __is_yaml_file(file: str):
    if Path(file).suffix in ['.yml', '.yaml']:
        return True
    else:
        ts_throw_error(TsErrCode.ERR_MMAP_2, os.path.basename(file))

def __is_rdl_file(file: str):
    if Path(file).suffix == '.rdl':
        return True
    else:
        ts_throw_error(TsErrCode.ERR_MMAP_3, os.path.basename(file))

def __ordt_valid_identifier(name):
    """ (very naive) If string is not a valid ORDT identifier name, convert it to one. """
    name = name.replace('{', '_').replace('}', '_')
    name = name.replace('[', '_').replace(']', '_')
    name = name.replace('(', '_').replace(')', '_')
    name = name.replace(' ', '_')
    return name

def ordt_build_parms_file(output_dir, ordt_parms_filename):
    """builds a parameters file with default parameters for ordt in the output directory"""

    default_parms = dedent("""\
        // rdl input parameters
        input rdl {
            resolve_reg_category    = true      // if register category is unspecified, try to determine from rdl
            lint_rdl                = false
        }

        // Latex output parameters
        output tslatexdoc {
            add_latex_preamble      = true 		// Add LaTex pre-amble (stand-alone document)
            add_latex_reg_summary   = true      // Add register summary table on top
            add_landscape_tables    = true	    // Add register table in landscape mode
        }
    """)

    with open(os.path.join(output_dir, ordt_parms_filename), 'w') as fp:
        fp.write(default_parms)

    return os.path.join(output_dir, ordt_parms_filename)

def __load_file(mode, target_filepath: str, current_level: typing.Optional[str] = None) -> typing.Tuple[dict, str]:
    """Load target_filepath relative to current file level,
        return either path or rendered yaml dictionary"""
    if mode == 'rdl':
        current_dir = Path(current_level).parent

        target = current_dir.joinpath(Path(target_filepath))
        if not target.exists():
            ts_throw_error(TsErrCode.ERR_MMAP_4, target)

        return target

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

def rdl_build_output(rdl_filepath, xml_filepath, ordt_parms_filepath):
    """ Take items in rdl elements list and build concatenated rdl file at :param output_filepath. """

    # pattern detecting start and end of addrmap element
    startAddrMapPattern = re.compile(r"addrmap\s*{")
    endAddrMapPattern = re.compile(r"\s*}\s*\w+\s*;")

    # addrMap string after all regfile objects
    addrMapStr  = "\naddrmap {"

    with open(rdl_filepath, 'w') as output_file:

        for rdl in rdl_list:

            # store rdlfiles as list of lines
            with open(rdl['reg_map'], 'r') as rdlFile:
                lines = rdlFile.readlines()

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

            rdl['name'] = __ordt_valid_identifier(rdl['name'])

            lines[start_index] = f"regfile {rdl['name']} {{"
            lines[end_index] = "};"

            output_file.writelines(lines[start_index : end_index + 1])

            # make addrmap string with base_addresses, this instantiates all regfile objects
            addrMapStr += "\n\texternal {0} TOP_{0}@{1};".format(rdl['name'], rdl['start_addr'])
            output_file.write("\n")

        # use top source file name as addrmap name
        addrMapStr += f'\n}} {__ordt_valid_identifier(os.path.splitext(os.path.basename(rdl_filepath))[0])};'
        output_file.write(addrMapStr)

    __ordt_run(rdl_filepath, xml_filepath, ordt_parms_filepath)

def render_yaml_parent(top_level_filepath):
    """ Renders yaml files and stores data for both types of outputs. """
    _MAX_NESTING_LEVEL = 5
    nesting_level = [1]

    def load_regions(rendered_yaml):
        nesting_level[0] += 1

        if nesting_level[0] >= _MAX_NESTING_LEVEL:
            raise RecursionError(f"Maximum nesting level reached: {_MAX_NESTING_LEVEL}")

        if 'regions' in rendered_yaml:
            # naive solution to force validate all nested nodes
            for region in rendered_yaml['regions']:
                    GRAMMAR_MEM_MAP_CONFIG.validate(region)

            for region in rendered_yaml['regions']:
                ts_warning(TsWarnCode.WARN_MMAP_0, region['name'])
                ts_info(TsInfoCode.INFO_MMAP_0, hex(region['start_addr']), hex(region['end_addr']))
                if "regions" in region and "reg_map" in region \
                    or "regions" not in region and "reg_map" not in region:
                    ts_throw_error(TsErrCode.ERR_MMAP_0, region['name'])

                if 'reg_map' in region and __is_rdl_file(region['reg_map']):
                    # region has no children if 'reg_map' key present
                    ts_debug("Including RDL file: {}".format(region['reg_map']))

                    region['reg_map'] = __load_file('rdl', region['reg_map'], current_level[-1])
                    rdl_list.append(region)

                elif 'regions' in region:

                    if __is_yaml_file(region['regions']):
                        ts_debug("Opening YAML file: {}".format(region['regions']))
                        temp_yaml, tmp_current_level = __load_file('yaml', region['regions'], current_level[-1])
                        current_level.append(tmp_current_level)
                        load_regions(temp_yaml)

                    else: load_regions(region)

            del current_level[-1]
            nesting_level [0] -= 1

        else:
            ts_throw_error(TsErrCode.ERR_MMAP_1, current_level[-1])

    rendered_yaml, tmp_current_level = __load_file('yaml', top_level_filepath, current_level = None)
    current_level.append(tmp_current_level)
    GRAMMAR_MEM_MAP_CONFIG.validate(rendered_yaml)
    ts_warning(TsWarnCode.WARN_MMAP_1, rendered_yaml['name'])
    ts_info(TsInfoCode.INFO_MMAP_0, hex(rendered_yaml['start_addr']), hex(rendered_yaml['end_addr']))
    load_regions(rendered_yaml)

