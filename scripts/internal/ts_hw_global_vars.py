# -*- coding: utf-8 -*-

####################################################################################################
# Global variables for Tropic Square Digital simulation scripting system
#
# TODO: License
####################################################################################################

import os


class TsGlobals:
    # Repository root environment variable
    TS_REPO_ROOT = "TS_REPO_ROOT"

    # Simulation directory
    TS_SIM_DIR = "sim"

    # Simulation config file path
    TS_SIM_CFG_PATH = os.path.join(TS_SIM_DIR, "ts_sim_config.yml")

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
    TS_SIM_JUNIT_SUMMARY_PATH = os.path.join(TS_SIM_LOG_DIR_PATH, "ts_sim_junit_out.xml")

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

