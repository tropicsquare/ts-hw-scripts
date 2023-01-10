# -*- coding: utf-8 -*-

####################################################################################################
# Global variables for Tropic Square Digital simulation scripting system
#
# TODO: License
####################################################################################################

from os.path import join


class TsGlobals:
    # Repository root environment variable
    TS_REPO_ROOT = "TS_REPO_ROOT"

    # Simulation directory
    TS_SIM_DIR = "sim"

    # Configuration directory
    TS_CFG_DIR = "cfg"

    # Power directory
    TS_PWR_DIR = "pwr"

    # Simulation config file path
    TS_SIM_CFG_PATH = join(TS_SIM_DIR, "ts_sim_config.yml")

    # Design config file path
    TS_DESIGN_CFG_PATH = join(TS_CFG_DIR, "ts_design_config.yml")

    # Power config file path
    TS_PWR_CFG_PATH = join(TS_PWR_DIR, "ts_pwr_config.yml")

    # Environment configuration script
    TS_CONFIG_ENV_SCRIPT = "source ./setup_env"

    # Default build directory
    TS_SIM_BUILD_PATH = join(TS_SIM_DIR, "build")

    # Log files directories
    TS_COMP_LOG_DIR_PATH = join(TS_SIM_DIR, "comp_logs")
    TS_ELAB_LOG_DIR_PATH = join(TS_SIM_DIR, "elab_logs")
    TS_SIM_LOG_DIR_PATH = join(TS_SIM_DIR, "sim_logs")

    # Coverage directory
    TS_COVERAGE_DIR_PATH = join(TS_SIM_DIR, "coverage_output")

    # Compilation log file
    TS_COMP_LOG_FILE_PATH = join(TS_COMP_LOG_DIR_PATH, "compile.log")
    TS_TMP_LOG_FILE_PATH = join(TS_COMP_LOG_DIR_PATH, "tmp.log")

    # Test specific log file path
    TS_SIM_LOG_FILE = None

    # Junit output path
    TS_SIM_JUNIT_SUMMARY_PATH = join(TS_SIM_LOG_DIR_PATH, "ts_sim_junit_out.xml")

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

    # Power configuration (Dictionary from YAML parser)
    TS_PWR_CFG = None

    # Power run dir
    TS_PWR_RUN_DIR = None

    # Runfile for power analysis
    TS_PWR_RUN_FILE = "modules/ts-power-flow/pwr/pwr.tcl"

    #
    TS_PNR_EXPORT_PATH = "/projects/tropic01/pnr_export"

    # Runcode
    TS_RUNCODE = None

    # Runcode directory
    TS_RUNCODE_DIR = None

    # Enviromantal variable for synthesis flow root directory ts-synthesis-flow
    TS_SYN_FLOW_PATH = 'TS_SYN_FLOW_PATH'

    # File path of dc.tcl to run synthesis
    TS_SYN_DC_RM_RUNFILE = 'ts_dc_syn_script.tcl'

    # File path of dc.tcl to run synthesis
    TS_SYN_DC_RM_OPENFILE = 'ts_dc_open_script.tcl'

    # Synthesis run dir
    TS_SYN_RUN_DIR = None

    # Synthesis sub-blocks build dir
    TS_SYN_BUILD_DIR = '.'

    # Synthesis log dir
    TS_SYN_LOGS_DIR = 'logs' 

    # Synthesis results dir
    TS_SYN_RESULTS_DIR = 'results'

    # Synthesis reports dir
    TS_SYN_REPORTS_DIR = 'reports'

    # Synthesis design_cfg file
    TS_SYN_DESIGN_CFG_FILE = 'design_cfg.tcl'

    # Synthesis setup.tcl file
    TS_SYN_SETUP_FILE = 'syn_setup.tcl'

    # Synthesis source rtl tcl file
    TS_SYN_SRC_RTL_FILE = 'src_rtl.tcl'

    # Synthesis RTL target
    TS_SYN_TARGET = None
