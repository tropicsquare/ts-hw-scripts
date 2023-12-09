# -*- coding: utf-8 -*-

####################################################################################################
# Global variables for Tropic Square Digital simulation scripting system
#
# For license see LICENSE file in repository root.
####################################################################################################

import os


class TsGlobals:
    # Repository root environment variable
    TS_REPO_ROOT = "TS_REPO_ROOT"

    # Runcode
    TS_RUNCODE = None

    # Simulation directory
    TS_SIM_DIR = "sim"

    # Configuration directory
    TS_CFG_DIR = "cfg"

    # Power directory
    TS_PWR_DIR = "pwr"

    # Simulation config file path
    TS_SIM_CFG_PATH = os.path.join(TS_SIM_DIR, "ts_sim_config.yml")

    # Design config file path
    TS_DESIGN_CFG_PATH = os.path.join(TS_CFG_DIR, "ts_design_config.yml")

    # Power config file path
    TS_PWR_CFG_PATH = os.path.join(TS_PWR_DIR, "ts_pwr_config.yml")

    # Environment configuration script
    TS_CONFIG_ENV_SCRIPT = "source ./setup_env"

    # Default build directory
    TS_SIM_BUILD_PATH = os.path.join(TS_SIM_DIR, "build")

    # Log files directories
    TS_COMP_LOG_DIR_PATH = os.path.join(TS_SIM_DIR, "comp_logs")
    TS_ELAB_LOG_DIR_PATH = os.path.join(TS_SIM_DIR, "elab_logs")
    TS_SIM_LOG_DIR_PATH = os.path.join(TS_SIM_DIR, "sim_logs")

    # Coverage directory
    TS_COVERAGE_DIR_PATH = os.path.join(TS_SIM_DIR, "coverage_output")

    # Compilation log file
    TS_COMP_LOG_FILE_PATH = os.path.join(TS_COMP_LOG_DIR_PATH, "compile.log")
    TS_TMP_LOG_FILE_PATH = os.path.join(TS_COMP_LOG_DIR_PATH, "tmp.log")

    # Test specific log file path
    TS_SIM_LOG_FILE = None

    # Junit output path
    TS_SIM_JUNIT_SUMMARY_PATH = os.path.join(
        TS_SIM_LOG_DIR_PATH, "ts_sim_junit_out.xml"
    )

    # Simulation configuration (Dictionary from YAML parser)
    TS_SIM_CFG = None

    # Test list - All available tests
    TS_TEST_LIST = None

    # Test list - All tests to be run in a single ts_sim_run.py/ts_sim_regress.py run
    TS_TEST_RUN_LIST = None

    # Maximal depth supported for list files nesting (before throwing exception on circular
    # dependency)
    MAX_LIST_FILE_DEPTH = 10

    # Source files loaded for compilation - linear
    TS_SIM_SRCS = None

    # Source files loaded for compilation - dictionary by compilation library
    TS_SIM_SRCS_BY_LIB = None

    # Design configuration (Dictionary from YAML parser)
    TS_DESIGN_CFG = None

    # List of PDK configurations loaded
    TS_PDK_CFGS = []

    # List of PDK views to be exported
    TS_EXP_VIEWS = []

    # Requirements Tracing directory
    TS_REQ_TRACING_DIR_PATH = os.path.join(TS_SIM_DIR, "req_tracing_output")

    # Power configuration (Dictionary from YAML parser)
    TS_PWR_CFG = None

    # Runfile for power analysis
    TS_PWR_RUN_FILE = "modules/ts-power-flow/pwr/pwr.tcl"

    TS_PWR_RUN_SCENARIOS = None

    #
    TS_PNR_EXPORT_PATH = "/projects/tropic01/pnr_export"

    # Runcode directory
    TS_PWR_RUNCODE_DIR = None

    # Enviromantal variable for synthesis flow root directory ts-synthesis-flow
    TS_SYN_FLOW_PATH = "TS_SYN_FLOW_PATH"

    # File path of dc.tcl to run synthesis
    TS_SYN_DC_RM_RUNFILE = "ts_dc_syn_script.tcl"

    # File path of dc.tcl to run synthesis
    TS_SYN_DC_RM_OPENFILE = "ts_dc_open_script.tcl"

    # Synthesis run dir
    TS_SYN_RUN_DIR = None

    # Synthesis sub-blocks build dir
    TS_SYN_BUILD_DIR = "."

    # Synthesis log dir
    TS_SYN_LOGS_DIR = "logs"

    # Synthesis results dir
    TS_SYN_RESULTS_DIR = "results"

    # Synthesis reports dir
    TS_SYN_REPORTS_DIR = "reports"

    # Synthesis design_cfg file
    TS_SYN_DESIGN_CFG_FILE = "design_cfg.tcl"

    # Synthesis setup.tcl file
    TS_SYN_SETUP_FILE = "syn_setup.tcl"

    # Synthesis source rtl tcl file
    TS_SYN_SRC_RTL_FILE = "src_rtl.tcl"

    # Synthesis multi-corner multi-mode setup file
    TS_SYN_MCMM_FILE = "mcmm_setup.tcl"

    # Synthesis DFT exception file
    TS_SYN_DFT_EXCEPTION_FILE = "dft_exception.tcl"

    # Synthesis DFT insertion file
    TS_SYN_DFT_INSERTION_FILE = "dft_insertion.tcl"

    # Synthesis RTL target
    TS_SYN_TARGET = None

    # Synthesis release dir
    TS_SYN_RELEASE_DIR = None

    # Enviromantal variable for synthesis flow root directory ts-synthesis-flow
    TS_STA_FLOW_PATH = "TS_STA_FLOW_PATH"

    # Runcode
    TS_STA_RUNCODE = None

    # File path of dc.tcl to run synthesis
    TS_STA_DC_RM_RUNFILE = "ts_pt_sta_script.tcl"

    # File path of dc.tcl to run synthesis
    TS_STA_DC_RM_OPENFILE = "ts_pt_open_script.tcl"

    # Netlist file
    TS_STA_DC_RM_NETLIST = None

    # Synthesis run dir
    TS_STA_RUN_DIR = None

    # Synthesis sub-blocks build dir
    TS_STA_BUILD_DIR = "."

    # Synthesis log dir
    TS_STA_LOGS_DIR = "logs"

    # Synthesis results dir
    TS_STA_RESULTS_DIR = "results"

    # Synthesis reports dir
    TS_STA_REPORTS_DIR = "reports"

    # Synthesis design_cfg file
    TS_STA_DESIGN_CFG_FILE = "design_cfg.tcl"

    # Synthesis setup.tcl file
    TS_STA_SETUP_FILE = "sta_setup.tcl"

    # Static timing analysis multi-corner multi-mode setup file
    TS_STA_DMSA_FILE = "dmsa_setup.tcl"

    # Static timing analysis release dir
    TS_STA_RELEASE_DIR = None

    # TODO: Clean-up this stuff coming from power flow!!!!
    TS_DIR_DONT_TOUCH = ["/projects/tropic01/pnr_export"]

    # Enviromental variable for DFT lint root directory
    TS_DFT_LINT_PATH = "lint"

    # DFT tools names
    TS_DFT_LINT_TOOL = "spyglass"
    TS_DFT_ATPG_TOOL = "atpg-tst"
    TS_DFT_RTL_TOOL = "rtl-tst"

    # DFT runcode
    TS_DFT_RUNCODE = None

    # DFT run dir
    TS_DFT_RUN_DIR = None

    # DFT run file name
    TS_DFT_RUNFILE = "dft_runfile.tcl"

    # DFT netlist
    TS_DFT_NETLIST = None

    # DFT constraint file
    TS_DFT_CONSTRAINT = None

    # DFT source rtl tcl file
    TS_DFT_SRC_RTL_FILE = "src_rtl.tcl"

    # DFT setup file
    TS_DFT_SETUP_FILE = "dft_setup.tcl"

    # DFT sub-blocks build dir
    TS_DFT_BUILD_DIR = "."

    # DFT log dir
    TS_DFT_LOGS_DIR = "logs"

    # DFT results dir
    TS_DFT_RESULTS_DIR = "results"

    # DFT reports dir
    TS_DFT_REPORTS_DIR = "reports"

    # DFT design_cfg file
    TS_DFT_DESIGN_CFG_FILE = "design_cfg.tcl"

    # Enviromental variable for RTL LINT root directory
    TS_RTL_LINT_PATH = "lint"

    # RTL LINT tools names
    TS_RTL_LINT_TOOL = "spyglass"

    # RTL LINT runcode
    TS_RLT_LINT_RUNCODE = None

    # RTL LINT run dir
    TS_RTL_LINT_RUN_DIR = None

    # RTL LINT run file name
    TS_RTL_LINT_RUNFILE = "rtl_lint_runfile.tcl"

    # RTL LINT constraint file
    TS_RTL_LINT_CONSTRAINT = None

    # RTL LINT source rtl tcl file
    TS_RTL_LINT_SRC_RTL_FILE = "src_rtl.tcl"

    # RTL LINT setup file
    TS_RTL_LINT_SETUP_FILE = "rtl_lint_setup.tcl"

    # RTL LINT sub-blocks build dir
    TS_RTL_LINT_BUILD_DIR = "."

    # RTL LINT log dir
    TS_RTL_LINT_LOGS_DIR = "logs"

    # RTL LINT results dir
    TS_RTL_LINT_RESULTS_DIR = "results"

    # RTL LINT reports dir
    TS_RTL_LINT_REPORTS_DIR = "reports"

    # RTL LINT design_cfg file
    TS_RTL_LINT_DESIGN_CFG_FILE = "design_cfg.tcl"

    # Enviromental variable for prn root directory
    TS_PNR_PATH = "pnr"

    # PNR tool name
    TS_PNR_TOOL = "icc2"

    # PNR runcode
    TS_PNR_RUNCODE = None

    # PRN run dir
    TS_PNR_RUN_DIR = None

    # PNR setup file
    TS_PNR_SETUP_FILE = "pnr_setup.tcl"

    # Synthesis design_cfg file
    TS_PNR_DESIGN_CFG_FILE = "design_cfg.tcl"

    # File path for open-file PNR tool
    TS_PNR_OPENFILE = "ts_pnr_open_script.tcl"

    # PNR log dir
    TS_PNR_LOGS_DIR = "logs"

    # PNR results dir
    TS_PNR_RESULTS_DIR = "results"

    # PNR reports dir
    TS_PNR_REPORTS_DIR = "reports"

    # PNR multi-corner multi-mode setup file
    TS_PNR_MCMM_FILE = "mcmm_setup.tcl"

    # PNR release dir
    TS_PNR_RELEASE_DIR = None
