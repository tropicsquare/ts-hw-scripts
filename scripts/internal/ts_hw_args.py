# -*- coding: utf-8 -*-

####################################################################################################
# Handling of script arguments.
#
# TODO: License
####################################################################################################

import os
from argparse import SUPPRESS, ArgumentParser, RawTextHelpFormatter
from textwrap import dedent

from .__version__ import __version__
from .ts_hw_common import ts_get_root_rel_path
from .ts_hw_global_vars import TsGlobals

__norm_join = lambda *paths: os.path.normpath(os.path.join(*paths))


class TsArgumentParser(ArgumentParser):
    def __init__(self, description):
        super().__init__(description=description, formatter_class=RawTextHelpFormatter)


def add_ts_common_args(parser):
    """
    Adds arguments which are common to all scripts (e.g. --verbose)
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Prints most important executed commands and actions. "
        "The more 'v', the more verbose the script.",
    )

    parser.add_argument(
        "-n",
        "--no-color",
        action="store_true",
        default=False,
        help="Do not use coloured output of the script.",
    )


def add_cfg_files_arg(parser):
    """
    Adds simulation and design config file arguments
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "-sc",
        "--sim-cfg",
        default=ts_get_root_rel_path(TsGlobals.TS_SIM_CFG_PATH),
        help="Overrides simulation config file, default is "
        f"${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_CFG_PATH)}",
    )
    parser.add_argument(
        "-dc",
        "--design-cfg",
        default=ts_get_root_rel_path(TsGlobals.TS_DESIGN_CFG_PATH),
        help="Specifies Design configuration file to load.",
    )
    parser.add_argument(
        "-pc",
        "--pwr-cfg",
        default=ts_get_root_rel_path(TsGlobals.TS_PWR_CFG_PATH),
        help="Specifies Power analysis configuration file to load.",
    )




def add_target_arg(parser):
    """
    Adds compilation/simulation target argument.
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "target",
        help="Design target from simulation config file "
        "(e.g. rtl, gate_min, gate_max)",
    )


def add_pdk_cfg_args(parser):
    """
    Adds PDK configuration arguments.
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--list-pdks", action="store_true", default=False, help="List available PDKs"
    )

    parser.add_argument(
        "--list-pdk-ips",
        action="store_true",
        help="Only list available IPs for loaded PDKs, do not export any config.",
    )

    parser.add_argument(
        "--list-pdk-std-cells",
        action="store_true",
        help="Only list available IPs for loaded PDKs, do not export any config.",
    )

    parser.add_argument(
        "--list-supported-views",
        action="store_true",
        help="Only list views supported by the scrip, do not export any config",
    )

    parser.add_argument(
        "--exp-tcl-file-dc",
        default="",
        help="Exports TCL file with sources for DC shell.",
    )

    parser.add_argument(
        "--exp-tcl-file-vivado",
        default="",
        help="Exports TCL file with sources for Vivado.",
    )

    parser.add_argument(
        "--exp-tcl-design-cfg",
        help="Export TCL file with design configuration (IPs (hard macros), standard cells) views",
    )

    parser.add_argument(
        "--add-views", help="Comma separated list of views to export (e.g. db,mw)"
    )

    parser.add_argument(
        "--add-top-entity", action="store_true", help="Export top entity (design name)."
    )

    parser.add_argument(
        "--add-syn-rtl-build-dirs",
        action="store_true",
        help="Export RTL build directories (per-library)",
    )

    parser.add_argument(
        "--add-constraints",
        action="store_true",
        help="Export constraints (global and per-mode)",
    )

    parser.add_argument(
        "--add-floorplan",
        action="store_true",
        help="Export of floorplan file path needed usually for synthesis.",
    )

    parser.add_argument(
        "--add-spef",
        action="store_true",
        help="Export of SPEF files paths per-mode needed usually for STA or PwR flows.",
    )

    parser.add_argument(
        "--add-map-tech",
        action="store_true",
        help="Export map and tech files paths needed usually for topological synthesis.",
    )

    parser.add_argument(
        "--add-tluplus",
        action="store_true",
        help="Exports Tlu+ files path and per modes rc_corners",
    )

    parser.add_argument(
        "--add-wireload", action="store_true", help="Exports wireload library settings."
    )

    parser.add_argument(
        "--add-opcond",
        action="store_true",
        help="Exports liberty files operation conditions according to a corner settings.",
    )



def add_ts_sim_compile_args(parser):
    """
    Adds arguments specific to ts_sim_compile.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--clear",
        action="store_true",
        default=False,
        help="Removes all previously compiled sources before compiling "
        "(forces recompilation of all files).",
    )

    parser.add_argument(
        "--clear-logs",
        action="store_true",
        default=False,
        help="Clear log file directories for compilation logs before compiling",
    )

    parser.add_argument(
        "--list-sources",
        action="store_true",
        default=False,
        help="Only list all files that will be compiled, do not run compilation. "
        "\nFiles to be compiled are target specific, and they are queried from "
        "source list files in simulator config file",
    )

    parser.add_argument(
        "--list-targets",
        action="store_true",
        default=False,
        help="Only list all targets available for compilation, "
        "do not run compilation.",
    )

    parser.add_argument(
        "--compile-debug",
        action="store_true",
        default=False,
        help="Forces compilation of all files in debug mode.",
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Forces compilation with coverage instrumentation.",
    )

    parser.add_argument(
        "--add-comp-options",
        default="",
        help="Adds extra compile options (switches) to a compile command issued "
        "to a simulator. Options are added for all compiled files.",
    )

    parser.add_argument(
        "--add-vhdl-comp-options",
        default="",
        help="Adds extra compile options to a compile command of a VHDL files.",
    )

    parser.add_argument(
        "--add-verilog-comp-options",
        default="",
        help="Adds extra compile options to a compile command of "
        "Verilog/System Verilog files.",
    )

    parser.add_argument(
        "--exp-tcl-file-dc",
        default="",
        help="Exports TCL file with sources for DC shell.",
    )

    parser.add_argument(
        "--exp-tcl-file-vivado",
        default="",
        help="Exports TCL file with sources for Vivado.",
    )

    parser.add_argument(
        "--build-dir",
        default=SUPPRESS,
        help="Overrides default build directory, default is "
        f"${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_SIM_BUILD_PATH)}",
    )

    parser.add_argument(
        "--gui",
        nargs="?",
        const="dve",
        default=None,
        choices=("dve", "verdi"),
        help="Compile options may depend on the GUI used for run. Default is '%(const)s'.",
    )

    parser.add_argument(
        "--simulator",
        help="Overrides used simulator. "
        "By default simulator is given by simulation config file.",
    )


def add_ts_sim_run_args(parser):
    """
    Adds arguments specific to ts_sim_run.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--add-elab-options",
        default="",
        help="Adds extra options to elaboration command line.",
    )

    parser.add_argument(
        "--add-sim-options",
        default="",
        help="Adds extra options to simulation command line.",
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        default=False,
        help="Removes all previously compiled sources before compiling "
        "(forces recompilation of all files).",
    )

    parser.add_argument(
        "--clear-logs",
        action="store_true",
        default=False,
        help="Clear log file directories for elaboration and simulation logs "
        "before running elaboration/simulation.",
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        default=False,
        help="Forces compilation with coverage instrumentation.",
    )

    parser.add_argument(
        "--dump-waves",
        action="store_true",
        default=False,
        help="When set, waves from whole simulation hierarchy are recorded",
    )

    parser.add_argument(
        "--elab-only",
        action="store_true",
        default=False,
        help="Run only elaboration (do not run simulation).",
    )

    parser.add_argument(
        "--sim-only",
        action="store_true",
        default=False,
        help="Run simulation only (do not run elaboration). "
        "Supersedes the '--elab-only' argument.",
    )

    parser.add_argument(
        "--check-elab-log",
        action="store_true",
        default=False,
        help="Check elaboration logs along with simulation logs.",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=False,
        help="When running multiple tests, if a test fail, "
        "finish and do not run next tests.",
    )

    parser.add_argument(
        "--gui",
        nargs="?",
        const="dve",
        default=None,
        choices=("dve", "verdi"),
        help="Launch simulation in GUI mode. Default is '%(const)s'.",
    )

    parser.add_argument(
        "--license-wait",
        action="store_true",
        default=False,
        help="When set, simulator waits for a license if it is not available.",
    )

    parser.add_argument(
        "--list-tests",
        action="store_true",
        default=False,
        help="Only print list of available tests, do not run simulation.",
    )

    parser.add_argument("--loop", type=int, default=1, help="Repeat each test N times.")

    parser.add_argument(
        "--no-check",
        action="store_true",
        default=False,
        help="Do not call 'ts_sim_check.py' after the run of the test.",
    )

    parser.add_argument(
        "--no-sim-out",
        action="store_true",
        default=False,
        help="Disable simulator output from elaboration and simulation "
        "to command line (Log file is still recorded).",
    )

    parser.add_argument(
        "--recompile",
        action="store_true",
        default=False,
        help="Force recompilation of the target before running simulation.",
    )

    parser.add_argument(
        "--seed", type=int, default=SUPPRESS, help="Seed for randomization."
    )

    parser.add_argument(
        "--session-file", default=SUPPRESS, help="Loads session file for GUI viewer."
    )

    parser.add_argument(
        "--do-file", default=SUPPRESS, help="Loads do file for simulator."
    )

    parser.add_argument(
        "--sim-verbosity",
        default="info",
        choices=("debug", "info", "warning", "error"),
        help="Specifies simulation verbosity, Default is '%(default)s'.",
    )

    parser.add_argument(
        "--exp-junit-logs",
        action="store_true",
        default=False,
        help="Export log files into JUnit output for Gitlab",
    )

    parser.add_argument("test_name", nargs="*", help="Name of the test to execute.")


def add_ts_sim_regress_args(parser):
    """
    Adds arguments specific to ts_sim_run.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--license-wait",
        action="store_true",
        default=False,
        help="When set, simulator waits for a license if it is not available.",
    )

    parser.add_argument(
        "--recompile",
        action="store_true",
        default=False,
        help="Force recompilation of the target before running simulation.",
    )

    parser.add_argument(
        "--regress-jobs", default=1, type=int, help="Number of parallel jobs to launch."
    )

    parser.add_argument(
        "--sim-verbosity",
        default="info",
        choices=("debug", "info", "warning", "error"),
        help="Specifies simulation verbosity, Default is '%(default)s'.",
    )

    parser.add_argument(
        "--exp-junit-logs",
        action="store_true",
        default=False,
        help="Export log files into JUnit output for Gitlab",
    )

    parser.add_argument(
        "--do-file", default=SUPPRESS, help="Loads do file for simulator."
    )

    parser.add_argument(
        "test_name", nargs="*", help="Name of the test/test group to execute."
    )

    parser.add_argument(
        "--check-elab-log",
        action="store_true",
        default=False,
        help="Check elaboration logs along with simulation logs.",
    )


def add_ts_sim_check_args(parser):
    """
    Adds arguments specific to ts_sim_check.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--exp-junit-logs",
        action="store_true",
        default=False,
        help="Export log files into JUnit output for Gitlab",
    )

    parser.add_argument(
        "log_file",
        nargs="+",
        help=dedent(
            f"""\
                        Path to log files.
                        Format is either:
                        - path relative to ${TsGlobals.TS_REPO_ROOT}
                        - absolute path"""
        ),
    )


def add_ts_sim_coverage_args(parser):
    """
    Adds arguments specific to ts_sim_coverage.py
    :param parser: Argparse parser to which arguments shall be added
    """

    parser.add_argument(
        "test",
        nargs="*",
        help=dedent(
            f"""\
                        Tests whose database is processed.
                        Format is either:
                        - test name
                        - path relative to ${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_COVERAGE_DIR_PATH)}
                        - absolute path"""
        ),
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        default=False,
        help=f"Remove ${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_COVERAGE_DIR_PATH)}",
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        default=False,
        help="Remove output database if previously created.",
    )

    parser.add_argument(
        "-e",
        "--elfile",
        help=f"Use exclusion file (location relative to ${TsGlobals.TS_REPO_ROOT})",
    )

    parser.add_argument(
        "--gui", action="store_true", default=False, help="Display results in GUI."
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        default=False,
        help="Do not generate report upon database merge",
    )

    parser.add_argument(
        "--no-sim-out",
        action="store_true",
        default=False,
        help="Disable output from merge.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=SUPPRESS,
        help=dedent(
            f"""\
                        Result database.
                        Format is either:
                        - database name
                        - path relative to ${__norm_join(TsGlobals.TS_REPO_ROOT, TsGlobals.TS_COVERAGE_DIR_PATH)}
                        - absolute path"""
        ),
    )


def add_ts_pwr_run_args(parser, tool_type):
    """
    Adds arguments specific to ts_run_pwr.py
    :param parser: Argparse parser to which arguments shall be added
    """

    parser.add_argument(
        "--clear-sim",
        action="store_true",
        default=False,
        help="Passe --clear option to simulation flow.",
    )

    parser.add_argument(
        "--clear-sim-logs",
        action="store_true",
        default=False,
        help="Passe --clear-logs option to simulation flow.",
    )
    parser.add_argument(
        "--clear-pwr-logs",
        action="store_true",
        default=False,
        help="Clear logs in pwr directory.",
    )

    parser.add_argument(
        "--recompile",
        action="store_true",
        default=False,
        help="Passe --recompile option to simulation flow.",
    )

    parser.add_argument(
        "--no-pwr-out",
        action="store_true",
        default=False,
        help="Disable output to command line (Log files are still recorded).",
    )

    parser.add_argument(
        "--no-sim",
        action="store_true",
        default=False,
        help=dedent(
            """\
            Simulation is not executed, default seed = 0.
            Flow expects dumped VCD file as if the simulation was executed.
            The inter.vcd file has to be located in sim/build/sim_<target>_<test>_<seed> directory.
            """
        ),
    )

    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        default=False,
        help="Lists all available scenarios defined in power config file."
    )

    parser.add_argument(
        "--open-pwr-waves",
        type=str,
        nargs="?",
        help="Shows power waves of scenario in GUI."
    )

    parser.add_argument(
        "--dump-pwr-waves",
        nargs="?",
        default=None,
        choices=("fsdb", "out"),
        help=dedent(
            """\
            Dumps power waves in specified format.
            """
        ),
    )

    parser.add_argument(
        "--add-scenario",
        type=str,
        nargs="?",
        help=dedent(
            """\
            Specify scenarios to run. If not present, all scenarios are runed."
            Example: --add-scenario=scen1,scen2,scen3
            --add-scenario=all runs all scenarios.
            """
        )
    )

    parser.add_argument(
        "--restore",
        type=str,
        nargs="?",
        help="Restore PrimeTime session of scenario."
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SUPPRESS,
        help="Seed for randomization. Overrides randomization specified in power config file."
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=False,
        help="When some non-crucial operation fails (e.g. simulation), "
        "do not continue and finish with error."
    )


def add_ts_mem_map_generator_args(parser):
    """
    Adds arguments specific to ts_memory_map_generator
    :param parser: Argparse parser to which arguments shall be added
    """

    parser.add_argument("--xml-dir")
    parser.add_argument("--latex-dir")
    parser.add_argument("--h-file",
                        help="One or multiple of (--latex-dir, --xml-dir, --h-file) required")
    parser.add_argument("--ordt-parms",
                        help=dedent("""\
                        Parameters file for ORDT XML output.
                        If a file is not specified, it will be created in the xml output directory.
                        """
        ),
    )
    parser.add_argument("--source-file", required=True)
    parser.add_argument(
        "--lint",
        action="store_true",
        help=dedent("""Script will refuse overlapping address ranges."""),
    )


def add_ts_syn_run_args(parser, tool_type):
    """
    Adds arguments specific to ts_syn_run.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--no-floorplan",
        action="store_true",
        default=False,
        help="No floorplan available",
    )

    parser.add_argument(
        "--topo",
        action="store_true",
        default=False,
        help=f"Topo mode for {tool_type}. Suggested to be used whenever floorplan available",
    )

    parser.add_argument(
        "--open-result",
        action="store_true",
        default=False,
        help=f"Open {tool_type} results of selected runcode.",
    )

    parser.add_argument(
        "--quick-run",
        action="store_true",
        default=False,
        help=f"Runs {tool_type} without optimization.",
    )

    parser.add_argument(
        "--break-after-link",
        action="store_true",
        default=False,
        help=f"Stops {tool_type} after linking the design.",
    )

    parser.add_argument(
        "--break-after-constraints",
        action="store_true",
        default=False,
        help=f"Stops {tool_type} after reading constraints file(s).",
    )

    parser.add_argument(
        "--break-after-compile",
        action="store_true",
        default=False,
        help=f"Stops {tool_type} after first compilation.",
    )

    parser.add_argument(
        "--break-after-reports",
        action="store_true",
        default=False,
        help=f"Stops {tool_type} after all reports are generated.",
    )


def add_ts_sta_run_args(parser, tool_type):
    """
    Adds arguments specific to ts_sta_run.py
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--open-result",
        action="store_true",
        default=False,
        help=f"Open {tool_type} results of selected runcode.",
    )

    parser.add_argument(
        "--checker",
        action="store_true",
        default=False,
        help=f"Open constraints checker for selected mode.",
    )

    parser.add_argument(
        "--sign-off", action="store_true", default=False, help=f"Run sign-off."
    )

    parser.add_argument(
        "--mode",
        nargs="?",
        default=None,
        help=f"Use mode name from ts_design_cfg.yml. Mutually exclusive with DMSA.",
    )

    parser.add_argument(
        "--netlist",
        nargs="?",
        default=None,
        help=f"Use relative path to the netlist file. It helps to overwrite default netlist naming pattern.",
    )

    parser.add_argument(
        "--dmsa",
        action="store_true",
        default=False,
        help=f"Run DMSA. Mutually exclusive with --mode",
    )

    parser.add_argument(
        "--sdc-export",
        action="store_true",
        default=False,
        help=f"Exports SDC 2.1 for PnR. Mutually exclusive with sign-off. It is suggested to use primarly in --dmsa mode as an complete batch run.",
    )


# Common argument --licence-wait
def add_lic_wait_arg(parser, tool_type):
    """
    Adds common argument --license-wait
    :param parser: Argparse parser to which arguments shall be added
    :param tool_type: String name of a tool to be displayed in help
    """
    parser.add_argument(
        "--license-wait",
        action="store_true",
        default=False,
        help=f"When set, {tool_type} waits for a licence until it is available.",
    )


# Common argument --runcode
def add_runcode_arg(parser):
    """
    Adds common argument --runcode <runcode_value>
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument("--runcode", nargs="?", default=None, help="Runcode.")


# Common argument --stay-in
def add_stayin_arg(parser, tool_type):
    """
    Adds common argument --stay-in-tool
    :param parser: Argparse parser to which arguments shall be added
    :param tool_type: String name of a tool to be displayed in help
    """
    parser.add_argument(
        "--stay-in-tool",
        action="store_true",
        default=False,
        help=f"Does not exit {tool_type} after run is done.",
    )


# Common argument --force
def add_force_arg(parser):
    """
    Adds common argument --force
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Delete previous results and run with the given runcode again.",
    )


# Common argument --release
def add_release_arg(parser):
    """
    Adds common argument --release
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--release",
        action="store_true",
        default=False,
        help="Hard-copy results to destination folder according to flow_dir settings in a ts_design_cfg.yml file.",
    )


# Common argument --source
def add_source_data_arg(parser, default=None):
    """
    Adds common argument --source-data
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--source-data",
        nargs="?",
        default=default,
        help=f"Source data from a destination folder according to flow_dir settings in a ts_design_cfg.yml file. Expected values: syn,sta,dft,pnr etc. Default value set is to {default}",
    )


# Common pdk/design_cfg argument --filter-mode-usage
def add_pd_common_args(parser, default=None):
    """
    Adds common pdk/design_cfg argument --filter-mode-usage
    :param parser: Argparse parser to which arguments shall be added
    """
    parser.add_argument(
        "--filter-mode-usage",
        nargs="?",
        default=default,
        choices= ('sim','syn','dft','sta','pnr','pwr','sta-signoff'),
        help=f"Defines filter for the usage attribute of a mode in ts_design_cfg.yml file. Expected values: syn,sta,dft,pnr etc."
    )


def add_ts_req_tracing_args(parser):
    """
    Adds arguments specific to ts_req_tracing.py
    :param parser: Argparse parser to which arguments shall be added
    """

    parser.add_argument("--spec-path",
                        help="Path to design specification")

    parser.add_argument("--ver-path",
                        help="Path to verification plan")

    parser.add_argument("-o", "--output",
                        help="Output directory with HTML report")

    parser.add_argument("--dump-db", action="store_true", default=False,
                        help="Generate YAML files with databases of traced items")

    parser.add_argument("--clear", action="store_true", default=False,
                        help="Remove output directory if previously created.")
