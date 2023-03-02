#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf-8 -*-

####################################################################################################
# Tropic Square Power Analysis Script
#
# Options
# scenario (scenario(s) to run)
# --runcude <runcode>
# --clear-pwr (clear all previous results in pwr/runs dir)
# --clear-sim (pass --clear option to ts_sim_run.py)
# --recompile (pass --recompile option to ts_sim_run.py)
# --gui (open generated FSDB in Verdi)
# --stay-in-pt-shell (stays in pt_shell)
# --loop <num> (if the scenario is randomized, runs it multiple times)
# --license-wait (pass --license-wait to ts_sim_run.py, waits on pt_shell license)
# --no-pwr-out (no output to cmd line)
# --list-scenarios (lists all available scenarios from pwr/ts-pwr-config.yml and ends)
# --dump-pwr-waves <fsdb/out>
# --no-sim (does not run simulation, expects previous run of the target+test with specified seed)
# --seed <seed> (specifies simulation seed)
#
# TODO: License
####################################################################################################

__author__ = "Vit Masek"
__copyright__ = "Tropic Square"
__license___ = "TODO"
__maintainer__ = "Vit Masek"

import os
import shutil
import sys

import argcomplete
from internal.ts_hw_args import (
    TsArgumentParser,
    add_cfg_files_arg,
    add_ts_common_args,
    add_ts_pwr_run_args,
    add_runcode_arg,
    add_force_arg,
    add_lic_wait_arg,
    add_stayin_arg,
    add_pd_common_args,
)
from internal.ts_hw_cfg_parser import (
    do_design_config_init,
    do_power_config_init,
    do_sim_config_init,
)
from internal.ts_hw_common import (
    exec_cmd_in_dir,
    init_signals_handler,
    ts_generate_seed,
    ts_get_root_rel_path,
    ts_unset_env_var,
)
from internal.ts_hw_global_vars import TsGlobals
from internal.ts_hw_logging import (
    TsColors,
    TsErrCode,
    TsInfoCode,
    TsWarnCode,
    ts_configure_logging,
    ts_debug,
    ts_info,
    ts_print,
    ts_throw_error,
    ts_warning,
)
from internal.ts_hw_pwr_support import *

if __name__ == "__main__":

    init_signals_handler()

    ################################################################################################
    # Parse arguments
    ################################################################################################
    parser = TsArgumentParser(description="Power analysis script")
    add_ts_common_args(parser)
    add_cfg_files_arg(parser)
    add_runcode_arg(parser)
    add_force_arg(parser)
    add_lic_wait_arg(parser,"pt_shell")
    add_stayin_arg(parser,"pt_shell")
    add_pd_common_args(parser)
    add_ts_pwr_run_args(parser,"pt_shell")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.clear_pwr_logs:
        ts_info(TsInfoCode.GENERIC, "Clearing pwr/logs directory.")
        ts_rmdir(os.path.join(ts_get_root_rel_path(TsGlobals.TS_PWR_DIR), "logs"))

    ts_configure_logging(args)
    pwr_logging(args)

    # Do Config Init
    do_sim_config_init(args)
    do_design_config_init(args)
    do_power_config_init(args)

    # Print available scenarios
    if args.list_scenarios:
        ts_print_available_scenarios()
        sys.exit(0)

    set_runcode(args)

    if (args.restore is not None):
        restore_pwr_session(args.restore)
        sys.exit(0)

    check_pwr_args(args)
    TsGlobals.TS_PWR_RUN_FILE = ts_get_root_rel_path(TsGlobals.TS_PWR_RUN_FILE)
    check_primetime_run_script()

    set_pwr_env(args)

    # Set license queuing for PrimeTime
    set_prime_time_license_queuing(args.license_wait)

    # Generate common design setup
    generate_common_setup()

    # Preset seed
    seed = 0
    if hasattr(args, "seed"):
        seed = args.seed

    ################################################################################################
    # Execute Scenarios
    ################################################################################################
    for pwr_scenario in TsGlobals.TS_PWR_RUN_SCENARIOS:
        this_loop = args.loop
        if (
            not get_optional_key(pwr_scenario, "randomized") or (hasattr(args, "seed"))
        ) and this_loop > 1:
            ts_warning(TsWarnCode.WARN_PWR_0, pwr_scenario["name"])
            this_loop = 1

        for i in range(this_loop):
            ########################################################################################
            # Simulate the scenario target and test
            ########################################################################################
            if not args.no_sim:
                ts_print(
                    "Running simulation for '{}'.".format(pwr_scenario["name"]),
                    color=TsColors.PURPLE,
                    big=True,
                )

                # Set seed
                if not hasattr(args, "seed"):
                    if get_optional_key(pwr_scenario, "randomized"):
                        seed = ts_generate_seed()
                    else:
                        seed = 0
                else:
                    seed = args.seed

                ts_info(TsInfoCode.GENERIC, f"Seed: {seed}")

                # Build command to run simulation
                run_sim_cmd = xterm_cmd_wrapper(build_run_sim_cmd(pwr_scenario, seed, args, clear=i))

                # Run simulation
                ts_debug(f"Running command {run_sim_cmd}")
                sim_exit_code = exec_cmd_in_dir_interactive(TsGlobals.TS_PWR_DIR, run_sim_cmd)

                ts_debug(f"Simulation exit code: {sim_exit_code}")

                if sim_exit_code:
                    if not args.fail_fast:
                        ts_warning(
                            TsWarnCode.GENERIC,
                            "Simulation failed on scenario {}... Continue...".format(
                                pwr_scenario["name"]
                            ),
                        )
                    else:
                        ts_throw_error(
                            TsErrCode.GENERIC,
                            "Simulation failed on scenario {}... Failing fast!".format(
                                pwr_scenario["name"]
                            ),
                        )

            vcd_file = check_vcd(pwr_scenario, seed)

            # Generate specific power setup
            generate_scenario_setup(pwr_scenario, vcd_file, args)

            # Generate post PrimeTime hook file
            generate_post_pwr_hook(pwr_scenario, args)

            # Generate PrimeTime command
            pt_shell_cmd = xterm_cmd_wrapper(build_prime_time_cmd(pwr_scenario))

            ts_print(
                "Running power analysis for '{}'.".format(pwr_scenario["name"]),
                color=TsColors.PURPLE,
                big=True,
            )

            # Run PrimeTime
            ts_debug(f"Running command {pt_shell_cmd}")
            pwr_exit_code = exec_cmd_in_dir_interactive(pwr_scenario["rundir"], pt_shell_cmd)

            ts_debug(f"PrimeTime exit code: {pwr_exit_code}")
            if pwr_exit_code:
                if not args.fail_fast:
                    ts_warning(
                        TsWarnCode.GENERIC,
                        "Power analysis failed on scenario {}... Continue".format(
                            pwr_scenario["name"]
                        ),
                    )
                else:
                    ts_throw_error(
                        TsErrCode.GENERIC,
                        "Power analysis failed on scenario {}... Failing fast".format(
                            pwr_scenario["name"]
                        ),
                    )

    ts_print("Power Analysis Done!", color=TsColors.PURPLE, big=True)

    ################################################################################################
    # Open power waves in GUI
    ################################################################################################
    #if args.gui == "verdi":
    #    # Set license queuing for Verdi
    #    set_verdi_license_queuing(args.license_wait)
    #    
    #    # Build command for Verdi and launch it
    #    pwr_wave_path = get_pwr_waves_path()
    #    verdi_cmd = f"verdi {pwr_wave_path}"
    #    verdi_exit_code = exec_cmd_in_dir(pwr_scenario["rundir"], f"verdi -sx {pwr_wave_path}",
    #                                      args.no_pwr_out, args.no_pwr_out)
    #
    #    ts_debug(f"Verdi exit code: {verdi_exit_code}")
    #    if verdi_exit_code:
    #        sys.exit(verdi_exit_code)

    # Unset all env variables set by this script
    ts_unset_env_var("SNPSLMD_QUEUE")
    ts_unset_env_var("NOVAS_LICENSE_QUEUE")

    sys.exit(0)
