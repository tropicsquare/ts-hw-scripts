#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square Requirement tracing script for tracing requirements and verification items
#
# For license see LICENSE file in repository root.
####################################################################################################

__author__ = "Marek Santa"
__copyright__ = "Tropic Square"
__license___ = "TODO:"
__maintainer__ = "Marek Santa"


import os
import re
import shutil
import sys

import argcomplete
import yaml
from internal.ts_hw_args import (
    TsArgumentParser,
    add_ts_common_args,
    add_ts_req_tracing_args,
)
from internal.ts_hw_common import init_signals_handler, ts_get_root_rel_path
from internal.ts_hw_global_vars import TsGlobals
from internal.ts_hw_logging import (
    TsErrCode,
    TsWarnCode,
    ts_configure_logging,
    ts_debug,
    ts_throw_error,
    ts_warning,
)

REQ_TRACING_OUTPUT_DIR = ts_get_root_rel_path(TsGlobals.TS_REQ_TRACING_DIR_PATH)
HTML_FILE_NAME = "req_tracing_result.html"


def read_file(filename):

    with open(filename, "r") as fd:
        lines = fd.readlines()

    # Remove comments and trim spaces; skip empy lines
    lines = list(filter(None, (re.sub(r"%.*", "", line).strip() for line in lines)))
    return lines


class RequirementTracing:
    def __init__(self, design_spec_path, ver_plan_path, output_path):
        # Get paths to design spec and verif plan
        self.design_spec_path = ts_get_root_rel_path(design_spec_path)
        self.verification_plan_path = ts_get_root_rel_path(ver_plan_path)

        # Get output path for HTML report
        if output_path:
            self.output_dir_path = os.path.join(TsGlobals.TS_REPO_ROOT, output_path)
        else:
            self.output_dir_path = REQ_TRACING_OUTPUT_DIR
        self.html_output_path = os.path.join(self.output_dir_path, HTML_FILE_NAME)

        # Initialize tracing dictionaries
        self.req_dict = {}
        self.vitem_dict = {}
        self.cov_dict = {}
        self.project_name = ""

    ################################################################################################
    # Parse content between matching curly brackets
    ################################################################################################
    def get_brackets_content(self, line, lines, line_no):
        """
        Parse content between matching curly brackets
        """
        # Number of unclosed brackets
        brackets_cnt = 0
        # Opening bracket found flag
        opening_bracket = False
        # Record output flag
        record_output = False
        # Position of corresponding closing bracket within the line
        char_pos = 0
        # Output string
        output = ""

        while True:
            # Parse characters in current line
            for i, char in enumerate(line):
                # Closing bracket
                if char == "}" and opening_bracket:
                    brackets_cnt -= 1
                    if brackets_cnt == 0:
                        # Corresponding closing bracket found,
                        # disable recording
                        record_output = False
                        char_pos = i
                        break

                if record_output:
                    output += char

                # Opening bracket
                if char == "{":
                    opening_bracket = True
                    brackets_cnt += 1
                    record_output = True

            if opening_bracket and not record_output:
                break

            line_no += 1
            line = lines[line_no]
        return output.strip(), line_no, char_pos

    ################################################################################################
    # Parse Design Specification file
    ################################################################################################
    def parse_design_spec(self):
        """
        Parse Design Specification file
        """

        # Open Design Spec and read lines
        ts_debug(f"Parsing design spec file '{self.design_spec_path}'")
        try:
            lines = read_file(self.design_spec_path)
        except FileNotFoundError:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"Design spec file '{self.design_spec_path}' does not exist.",
            )

        _looking_for_project_name = True
        _looking_for_req_start = True

        for line_no, line in enumerate(lines):

            # #####
            # Parse project name
            # #####
            if _looking_for_project_name:
                match = re.search(r"\\def\s+\\projectname\s*{(.*?)}", line)
                if match:
                    self.project_name = match[1]
                    ts_debug(f"Parsed project name: {self.project_name}")
                    _looking_for_project_name = False

            # #####
            # Parse requirements
            # #####
            if _looking_for_req_start and "\ReqStart" in line:
                rest_of_line = line.split("\ReqStart")[1]
                req_section_name, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                req_cnt = 0

            elif "\ReqItem" in line or "\ReqSubItem" in line:
                # Create requirement tag
                if "\ReqItem" in line:
                    req_cnt += 1
                    sub_req_cnt = 0
                    req_tag = f"REQ_{req_section_name}_{req_cnt}"
                else:
                    sub_req_cnt += 1
                    req_tag = f"REQ_{req_section_name}_{req_cnt}_{sub_req_cnt}"

                self.req_dict[req_tag] = {
                    "status": "N/A",
                    "description": "N/A",
                    "vitems": [],
                }

                # Parse requirement status
                rest_of_line = re.search(".*\\\\Req(Sub|)Item(.*)", line)[2]
                status, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                if status == "1":
                    self.req_dict[req_tag]["status"] = "Designed"
                elif status == "2":
                    self.req_dict[req_tag]["status"] = "Obsolete"
                else:
                    self.req_dict[req_tag]["status"] = "Not Designed"

                # Parse requirement description
                if new_line_no == line_no:
                    rest_of_line = rest_of_line[char_pos:]
                else:
                    rest_of_line = lines[new_line_no][char_pos:]
                    line_no = new_line_no
                description, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                print(f"{description}")
                print("-" * 150)
                self.req_dict[req_tag]["description"] = self.latex2html(description)

                ts_debug(
                    f"Parsed requirement:\n"
                    + "  Tag:         "
                    + req_tag
                    + "\n"
                    + "  Status:      "
                    + self.req_dict[req_tag]["status"]
                    + "\n"
                    + "  Description: "
                    + self.req_dict[req_tag]["description"]
                )

    ################################################################################################
    # Parse Verification Plan file
    ################################################################################################
    def parse_verif_plan(self):
        """
        Parse Verification Plan file
        """

        # Open Verification Plan and read lines
        ts_debug(f"Parsing verification plan file '{self.verification_plan_path}'")
        try:
            lines = read_file(self.verification_plan_path)
        except FileNotFoundError:
            ts_throw_error(
                TsErrCode.GENERIC,
                f"Verification plan file '{self.verification_plan_path}' does not exist.",
            )

        for line_no, line in enumerate(lines):

            # #####
            # Parse verification items
            # #####
            if "\VerItemStart" in line:
                rest_of_line = re.search(".*\\\\VerItemStart(.*)", line)[1]
                vitem_section_name, line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                vitem_cnt = 0

            elif (
                "\VerItemEnd" in line
                or "\VerSubItemStart" in line
                or "\VerSubItemEnd" in line
            ):
                # Do nothing
                continue

            elif "\VerItem" in line or "\VerSubItem" in line:
                # Create verification item tag
                if "\VerItem" in line:
                    vitem_cnt += 1
                    sub_vitem_cnt = 0
                    vitem_tag = f"VIT_{vitem_section_name}_{vitem_cnt}"
                else:
                    sub_vitem_cnt += 1
                    vitem_tag = f"VIT_{vitem_section_name}_{vitem_cnt}_{sub_vitem_cnt}"

                self.vitem_dict[vitem_tag] = {
                    "status": "N/A",
                    "description": "N/A",
                    "covers": [],
                }

                # Parse verification item status
                rest_of_line = re.search(".*\\\\Ver(Sub|)Item(.*)", line)[2]
                reqs, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                reqs_list = reqs.split(",")
                for req_tag_plain in reqs_list:
                    req_tag = req_tag_plain.strip().strip(",")
                    if req_tag in self.req_dict:
                        self.req_dict[req_tag]["vitems"].append(vitem_tag)
                    else:
                        ts_warning(
                            TsWarnCode.GENERIC,
                            f"Verification item '{vitem_tag}' is mapped to non-existing requirement '{req_tag}'",
                        )

                # Parse verification item tracing
                if new_line_no == line_no:
                    rest_of_line = rest_of_line[char_pos:]
                else:
                    rest_of_line = lines[new_line_no][char_pos:]
                    line_no = new_line_no
                status, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                if status == "1":
                    self.vitem_dict[vitem_tag]["status"] = "Verified"
                elif status == "2":
                    self.vitem_dict[vitem_tag]["status"] = "Obsolete"
                else:
                    self.vitem_dict[vitem_tag]["status"] = "Not Verified"

                # Parse verification item description
                if new_line_no == line_no:
                    rest_of_line = rest_of_line[char_pos:]
                else:
                    rest_of_line = lines[new_line_no][char_pos:]
                    line_no = new_line_no
                description, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                self.vitem_dict[vitem_tag]["description"] = self.latex2html(description)

                ts_debug(
                    f"Parsed verification item:\n"
                    + "  Tag:         "
                    + vitem_tag
                    + "\n"
                    + "  Status:      "
                    + self.vitem_dict[vitem_tag]["status"]
                    + "\n"
                    + "  Description: "
                    + self.vitem_dict[vitem_tag]["description"]
                    + "\n"
                    + "  Tracing:     "
                    + reqs
                )

            # #####
            # Parse assertions
            # #####
            if "\\vitAssert" in line:
                # Parse verification item tag
                rest_of_line = re.search(".*\\\\vitAssert(.*)", line)[1]
                vitem_tag, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )

                # Parse assertions
                if new_line_no == line_no:
                    rest_of_line = rest_of_line[char_pos:]
                else:
                    rest_of_line = lines[new_line_no][char_pos:]
                    line_no = new_line_no
                assertions, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )

                assertions_list = assertions.split("\n")
                for assertion in assertions_list:
                    self.vitem_dict[vitem_tag]["covers"].append(assertion.strip())
                    self.cov_dict[assertion.strip()] = {
                        "type": "assertion",
                        "description": "N/A",
                    }

                ts_debug(
                    f"Parsed assertion:\n"
                    + "  Verif Item:  "
                    + vitem_tag
                    + "\n"
                    + "  Assertions:  "
                    + ", ".join(self.vitem_dict[vitem_tag]["covers"])
                )

            # #####
            # Parse coverage
            # #####
            if "\coverPoint" in line or "\coverCross" in line or "\coverProp" in line:
                # Parse coverage item tag
                rest_of_line = re.search(".*\\\\cover(Point|Cross|Prop)(.*)", line)[2]
                cov_tag, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )

                self.cov_dict[cov_tag] = {"type": "coverage", "description": "N/A"}

                # Parse coverage description
                if new_line_no == line_no:
                    rest_of_line = rest_of_line[char_pos:]
                else:
                    rest_of_line = lines[new_line_no][char_pos:]
                    line_no = new_line_no
                description, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )
                self.cov_dict[cov_tag]["description"] = self.latex2html(description)

                # Parse verification items
                if new_line_no == line_no:
                    rest_of_line = rest_of_line[char_pos:]
                else:
                    rest_of_line = lines[new_line_no][char_pos:]
                    line_no = new_line_no
                vitems, new_line_no, char_pos = self.get_brackets_content(
                    rest_of_line, lines, line_no
                )

                vitems_list = vitems.split(",")
                for vitem_tag_plain in vitems_list:
                    vitem_tag = vitem_tag_plain.strip().strip(",")
                    if vitem_tag in self.vitem_dict:
                        self.vitem_dict[vitem_tag]["covers"].append(cov_tag)
                    else:
                        ts_warning(
                            TsWarnCode.GENERIC,
                            f"Coverage '{cov_tag}' is mapped to non-existing verification item '{vitem_tag}'",
                        )

                ts_debug(
                    f"Parsed coverage item:\n"
                    + "  Tag:         "
                    + cov_tag
                    + "\n"
                    + "  Type:        "
                    + self.cov_dict[cov_tag]["type"]
                    + "\n"
                    + "  Description: "
                    + self.cov_dict[cov_tag]["description"]
                    + "\n"
                    + "  Tracing:     "
                    + vitems
                )

    ################################################################################################
    # Dump parsed data to YAML files
    ################################################################################################
    def dump_parsed_data(self):
        """
        Dump parsed data to YAML files
        """

        ts_debug(f"Dumping parsed data to '{self.output_dir_path}'")

        parsed_req = os.path.join(self.output_dir_path, "parsed_req.yml")
        with open(parsed_req, "w") as fd:
            yaml.dump(self.req_dict, fd)

        parsed_vitem = os.path.join(self.output_dir_path, "parsed_vitem.yml")
        with open(parsed_vitem, "w") as fd:
            yaml.dump(self.vitem_dict, fd)

        parsed_cov = os.path.join(self.output_dir_path, "parsed_cov.yml")
        with open(parsed_cov, "w") as fd:
            yaml.dump(self.cov_dict, fd)

    ################################################################################################
    # Print HTML Output
    ################################################################################################
    def print_html_output(self):
        """
        Print HTML output
        """

        ts_debug(f"Printing HTML output to file '{self.html_output_path}'")

        f = open(self.html_output_path, "w")
        f.write("<!DOCTYPE html>\n")
        f.write('<html lang="en-us">\n')
        f.write("  <head>\n")
        f.write('    <meta charset="utf-8">\n')
        f.write("    <title>" + self.project_name + " Trace Matrix</title>\n")
        f.write("    <style>\n")
        f.write("      body {\n")
        f.write("        max-width: 960px;\n")
        f.write("        margin: auto;\n")
        f.write("      }\n")
        f.write("      h1 {\n")
        f.write("        padding-top: 20px;\n")
        f.write("      }\n")
        f.write("      table, th, td {\n")
        f.write("        border: 1px solid rgb(88, 75, 75);\n")
        f.write("        border-collapse: collapse;\n")
        f.write("        padding: 5px;\n")
        f.write("      }\n")
        f.write("      .tooltip {\n")
        f.write("        position: relative;\n")
        f.write("        display: inline-block;\n")
        f.write("        border-bottom: 1px dotted black;\n")
        f.write("      }\n")
        f.write("      .tooltip .tooltiptext {\n")
        f.write("        visibility: hidden;\n")
        f.write("        width: 500px;\n")
        f.write("        background-color: black;\n")
        f.write("        color: #fff;\n")
        f.write("        text-align: center;\n")
        f.write("        border-radius: 6px;\n")
        f.write("        padding: 5px 0;\n")
        f.write("        /* Position the tooltip */\n")
        f.write("        position: absolute;\n")
        f.write("        z-index: 1;\n")
        f.write("        top: 100%;\n")
        f.write("        left: 50%;\n")
        f.write("        margin-left: -60px;\n")
        f.write("      }\n")
        f.write("      .tooltip:hover .tooltiptext {\n")
        f.write("        visibility: visible;\n")
        f.write("      }\n")
        f.write("      .bg_color_red {\n")
        f.write("        background-color: #FF4D4D;\n")
        f.write("      }\n")
        f.write("      .bg_color_green {\n")
        f.write("        background-color: #66FF66;\n")
        f.write("      }\n")
        f.write("      .bg_color_grey {\n")
        f.write("        background-color: #ABABAB;\n")
        f.write("      }\n")
        f.write("    </style>\n")
        f.write("  </head>\n")
        f.write("  <body>\n")
        f.write("    <h1>" + self.project_name + " Trace Matrix</h1>\n")
        f.write("    <table>\n")
        f.write("      <tr>\n")
        f.write("        <th>Requirement</th>\n")
        f.write("        <th>Verification Item</th>\n")
        f.write("        <th>Assertion/Coverage</th>\n")
        f.write("      </tr>\n")

        for req_tag in self.req_dict:
            vitem_list = self.req_dict[req_tag]["vitems"]
            vitem_no = len(vitem_list)

            # Count number of rows in the table for requirement
            for vitem_tag in vitem_list:
                cp_no = len(self.vitem_dict[vitem_tag]["covers"])
                if cp_no > 0:
                    vitem_no += cp_no - 1

            # Get background color for requirement cell
            color = self.select_color(self.req_dict[req_tag]["status"])

            if vitem_no == 0:
                # Row in the table for requirement without traced verification item
                f.write("      <tr>\n")
                f.write(
                    "        <td "
                    + color
                    + '><div class="tooltip">'
                    + req_tag
                    + '<div class="tooltiptext">'
                    + self.req_dict[req_tag]["description"]
                    + "</div></div></td>\n"
                )
                f.write(
                    '        <td class="bg_color_red">Missing Verification Item</td>\n'
                )
                f.write(
                    '        <td class="bg_color_grey">No Assertion/Coverage</td>\n'
                )
                f.write("      </tr>\n")
            else:
                # Cell in the table for requirement
                f.write("      <tr>\n")
                f.write(
                    "        <td "
                    + color
                    + " rowspan="
                    + str(vitem_no)
                    + '><div class="tooltip">'
                    + req_tag
                    + '<div class="tooltiptext">'
                    + self.req_dict[req_tag]["description"]
                    + "</div></div></td>\n"
                )

                for i, vitem_tag in enumerate(vitem_list):
                    # Set color based on verification item status
                    color = self.select_color(self.vitem_dict[vitem_tag]["status"])
                    # Insert new row if this is not the first Verificatiom Item mapped
                    # to current requirement
                    if i > 0:
                        f.write("      <tr>\n")

                    if len(self.vitem_dict[vitem_tag]["covers"]) == 0:
                        # Cells in the table for Verification item without traced coverpoint or assertion
                        f.write(
                            "        <td "
                            + color
                            + '><div class="tooltip">'
                            + str(vitem_tag)
                            + '<div class="tooltiptext">'
                            + self.vitem_dict[vitem_tag]["description"]
                            + "</div></div></td>\n"
                        )
                        f.write(
                            '        <td class="bg_color_grey">No Assertion/Coverage</td>\n'
                        )
                        f.write("      </tr>\n")
                    else:
                        # Cell in the table for Verification item
                        f.write(
                            "        <td "
                            + color
                            + " rowspan="
                            + str(len(self.vitem_dict[vitem_tag]["covers"]))
                            + '><div class="tooltip">'
                            + str(vitem_tag)
                            + '<div class="tooltiptext">'
                            + self.vitem_dict[vitem_tag]["description"]
                            + "</div></div></td>\n"
                        )
                        for i, cp_or_assert_tag in enumerate(
                            self.vitem_dict[vitem_tag]["covers"]
                        ):
                            # Insert new row if this is not the first coverpoint/assertion mapped
                            # to current verification item
                            if i > 0:
                                f.write("      <tr>\n")

                            if self.cov_dict[cp_or_assert_tag]["type"] == "coverage":
                                f.write(
                                    '        <td><div class="tooltip">'
                                    + str(cp_or_assert_tag)
                                    + '<div class="tooltiptext">'
                                    + self.cov_dict[cp_or_assert_tag]["description"]
                                    + "</div></div></td>\n"
                                )
                            else:
                                f.write(
                                    "        <td>" + str(cp_or_assert_tag) + "</td>\n"
                                )
                            f.write("      </tr>\n")

        f.write("    </table>\n")
        f.write("  </body>\n")
        f.write("</html>\n")
        f.close()

    ################################################################################################
    # Select color according to status of requirement or verification item
    ################################################################################################
    def select_color(self, text):
        if text in ["Designed", "Verified"]:
            color = ' class="bg_color_green"'
        elif text in ["Not Designed", "Not Verified"]:
            color = ' class="bg_color_red"'
        elif text == "Obsolete":
            color = ' class="bg_color_grey"'
        return color

    ################################################################################################
    # Remove white spaces
    ################################################################################################
    def remove_white_spaces(self, text):
        text = re.sub("\s{2,}", " ", text)
        text = re.sub("\\\\newline", "\n", text)
        return text

    ################################################################################################
    # Itemize
    ################################################################################################
    def itemize(self, text):
        result = ""
        text = re.split("\\\\item", text)
        for i in range(len(text)):
            if i > 0:
                text[i] = f"<li>{text[i]}"
                if not re.search("\\\\end{(itemize|description)}", text[i]):
                    text[i] = f"{text[i]}</li>"
            text[i] = re.sub("\\\\begin{(itemize|description)}", "<ul>\n", text[i])
            text[i] = re.sub(
                "\\\\end{(itemize|description)}", "  </li>\n</ul>\n", text[i]
            )
            result += text[i]
        return result

    ################################################################################################
    # Latex substitution
    ################################################################################################
    def latex_substitution(self, text, pattern, substitution):
        result = ""
        pat_end = ""
        lst = re.split(pattern, text)
        if substitution != "":
            pat_end = f"{substitution[:1]}/{substitution[1:]}"
        for i in range(len(lst)):
            if i > 0:
                lst[i] = substitution + lst[i]
                lst[i] = lst[i].replace("}", pat_end, 1)
            result += lst[i]
        return result

    ################################################################################################
    # Replace projectname
    ################################################################################################
    def replace_projectname(self, text, project_name):
        return re.sub("\\\\projectname({}|)", project_name, text)

    ################################################################################################
    # Latex to HTML
    ################################################################################################
    def latex2html(self, text):
        text = self.remove_white_spaces(text)
        text = self.itemize(text)
        text = self.latex_substitution(text, "\\\\textbf{", "<b>")
        text = self.latex_substitution(text, "\\\\textit{", "<i>")
        text = self.latex_substitution(text, "\\\\Signal{", "<i>")
        text = self.latex_substitution(text, "\\\\Register{", "<b>")
        text = self.replace_projectname(text, self.project_name)
        return text


################################################################################################
# Tracing
################################################################################################
def tracing(args):
    exit_code = 0

    rt = RequirementTracing(args.spec_path, args.ver_path, args.output)

    if args.clear:
        ts_debug(f"Removing {rt.output_dir_path}")
        exit_code = shutil.rmtree(rt.output_dir_path, ignore_errors=True)

    os.makedirs(rt.output_dir_path, exist_ok=True)

    # Parse design spec
    rt.parse_design_spec()
    # Parse verif plan
    rt.parse_verif_plan()
    # Print YAML databases
    if args.dump_db:
        rt.dump_parsed_data()
    # Print HTML
    rt.print_html_output()

    return exit_code


if __name__ == "__main__":

    init_signals_handler()

    # Add script arguments
    parser = TsArgumentParser(description="Requirements tracing script")
    add_ts_common_args(parser)
    add_ts_req_tracing_args(parser)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ts_configure_logging(args)

    # Launch tracing
    sys.exit(tracing(args))
