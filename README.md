# Tropic Square HW design scripts

This repository contains scripts for HW design, such as scripts to run
simulations, regressions and/or analyze code coverage.

Released version of this repository is placed in `/tools/tropic`.

## How to use this repository

1. Check `ts_sw_cfg.py --list-sw` for latest version of ts-hw-scripts.
2. Place an entry into `ts_sw_cfg.yml` of your repository.
3. Call `source ./setup_env` to append scripts to `PATH` variable.

## User manual

To find out how to set-up the scripts and start using them, see:
[User manual](https://tropic-gitlab.corp.sldev.cz/internal/development-environment/ts-hw-scripts/-/jobs/artifacts/master/file/public/ts_sim_user_guide.pdf?job=pages).

## Examples

Examples of simulation configuration files, source list files and test list
files can be found in `example` folder.

Each sub-folder within `example` folder contains an example which demonstrates
particular functionality of the scripting system (e.g. how to define source
lists, how to define nested lists, how to define compilation/elaboration options
or how to configure hooks).

## Bug reports / Feature requests

If you encounter a bug, or you would like to have another feature in Tropic
Square HW scripting system, please open Issue on Gitlab (see "Issues" in
panel on the left.) Please, add a label which classifies the issue as either
bug or feature.

## Specification ##

The scripting system has specification which lays down requirements on all features.
The  specification tries to abstract away the details of particular implementation
(e.g. format of source-list files, keywords, etc...), it rather firmly defines what
the system should know. See:
[Specification](https://tropic-gitlab.corp.sldev.cz/internal/development-environment/ts-hw-scripts/-/jobs/artifacts/master/file/public/ts_sim_specification.pdf?job=pages).

## Development notes

Maintain following rules when writing/modyfing scripts in this repository:
- Use Python (Version 3.6+).
- The flow of adding new feature is following
  1. Specify it in design specification (write requirement)
  2. Implement the feature
  3. Describe the feature in User manual.
  4. Add an example (`example` folder and a simple test excercising this feauture).
- Avoid Python modules which are not installed in default Python installation
  (no fancy Jinja web developer crap...), follow KISS principle.
  If we use these modules, we would need to provide a docker image in which
  these modules will be present! This might be a problem because scripts
  from this repository will be used to launch VCS and DC Shell
