# Tropic Square HW design scripts

This repository contains scripts for HW design:
- Compile RTL/TB
- Run simulations and check test results
- Analyze and merge code coverage
- Hold, reference and use configuration of PDK views (analog macros, standard cells)
- Export RTL for synthesis
- Run scenario based power analysis of digital logic on gate level annotated design.
- Run synthesis

## Documentation

[User manual](https://tropic-gitlab.corp.sldev.cz/internal/development-environment/ts-hw-scripts/-/jobs/artifacts/master/raw/public/ts_sim_user_guide.pdf?job=build_docs).

[Memory map generator User manual](https://tropic-gitlab.corp.sldev.cz/internal/development-environment/ts-hw-scripts/-/jobs/artifacts/master/raw/public/ts_mem_map_generate_user_guide.pdf?job=build_docs).

[Power analysis User manual](https://tropic-gitlab.corp.sldev.cz/internal/development-environment/ts-hw-scripts/-/jobs/artifacts/master/raw/public/ts_pwr_user_guide.pdf?job=build_docs).

[Synthesis flow User manual](https://tropic-gitlab.corp.sldev.cz/internal/development-environment/ts-hw-scripts/-/jobs/artifacts/master/raw/public/ts_syn_user_guide.pdf?job=build_docs).

## Examples

Examples of configuration files, source list files and test list files can be
found in subfolders of `example` folder.

Each sub-folder within `example` folder contains an example which demonstrates
particular functionality of the scripting system (e.g. how to define source
lists, how to define nested lists, how to define compilation/elaboration options
or how to configure hooks).

Note: Examples are not publicly available due to sensitive PDK information!

## Templates

Templates of various config files can be found in `templates` folder. Following
templates are available:
  - Simulation config file (`ts_sim_cfg.yml`)
  - Test list file (`tlf.yml`)
  - Source list file (`slf.yml`)
  - Design config file (`ts_design_cfg.yml`) - Not publicly available due to sensitive PDK information!
  - PDK config file (`ts_sim_cfg.yml`) - Not publicly available due to sensitive PDK information!
  - Power scenarios config file (`ts_pwr_config.yml`)

## Bug reports / Feature requests

If you encounter a bug, or you would like to have another feature in Tropic
Square HW scripting system, please open Issue on Gitlab (see "Issues" in
panel on the left.) Please, add a label which classifies the issue as either
bug or feature.

## Development notes

Maintain following rules when writing/modifing scripts in this repository:
- The flow of adding new feature is following
  1. Implement the feature
  2. Describe the feature in User manual or create another document which documents
     your new feature. Each feature is typically Python script which can be launched
     from command line.
  3. Add an example to `example` folder.
  4. Add a test in `tests` folder.
- Try to avoid adding additional dependecies unless **REALLY** needed! If you need
  to write 100 lines of code, then write them instead of including another
  dependency! If you need to write 10K lines of code, then use a module instead!

## Dependencies

Current implementation of `ts-hw-scripts` uses Python 3.8 with following dependencies:
- `jinja`
- `pyaml`
- `schema`
- `junit_xml`
- `argcomplete`
- `psutil`
- `pydantic`
