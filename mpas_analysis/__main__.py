#!/usr/bin/env python
# This software is open source software available under the BSD-3 license.
#
# Copyright (c) 2022 Triad National Security, LLC. All rights reserved.
# Copyright (c) 2022 Lawrence Livermore National Security, LLC. All rights
# reserved.
# Copyright (c) 2022 UT-Battelle, LLC. All rights reserved.
#
# Additional copyright and license information can be found in the LICENSE file
# distributed with this code, or at
# https://raw.githubusercontent.com/MPAS-Dev/MPAS-Analysis/master/LICENSE

"""
Runs MPAS-Analysis via a configuration file (e.g. `analysis.cfg`)
specifying analysis options.
"""
# Authors
# -------
# Xylar Asay-Davis, Phillip J. Wolfram, Milena Veneziani

import mpas_analysis

import argparse
import sys
import os
import xarray
import time

from mache import discover_machine, MachineInfo

from mpas_tools.config import MpasConfigParser

from mpas_analysis.shared.io.utility import build_config_full_path, \
    make_directories, copyfile

from mpas_analysis.shared.html import generate_html

from mpas_analysis.shared.plot.colormap import register_custom_colormaps, \
    _plot_color_gradients

from mpas_analysis.framework.tasks import build_analysis_list
from mpas_analysis.framework.setup import purge_output, symlink_main_run,\
    update_generate, determine_analyses_to_generate, setup_analysis
from mpas_analysis.framework.run import run_analysis


def main():
    """
    Entry point for the main script ``mpas_analysis``
    """

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-v', '--version',
                        action='version',
                        version='mpas_analysis {}'.format(
                                mpas_analysis.__version__),
                        help="Show version number and exit")
    parser.add_argument("--setup_only", dest="setup_only", action='store_true',
                        help="If only the setup phase, not the run or HTML "
                        "generation phases, should be executed.")
    parser.add_argument("--html_only", dest="html_only", action='store_true',
                        help="If only the setup and HTML generation phases, "
                        "not the run phase, should be executed.")
    parser.add_argument("-g", "--generate", dest="generate",
                        help="A list of analysis modules to generate "
                        "(nearly identical generate option in config file).",
                        metavar="ANALYSIS1[,ANALYSIS2,ANALYSIS3,...]")
    parser.add_argument("-l", "--list", dest="list", action='store_true',
                        help="List the available analysis tasks")
    parser.add_argument("-p", "--purge", dest="purge", action='store_true',
                        help="Purge the analysis by deleting the output"
                        "directory before running")
    parser.add_argument("config_file", metavar="CONFIG", type=str, nargs='*',
                        help="config file")
    parser.add_argument("--plot_colormaps", dest="plot_colormaps",
                        action='store_true',
                        help="Make a plot displaying all available colormaps")
    parser.add_argument("--verbose", dest="verbose", action='store_true',
                        help="Verbose error reporting during setup-and-check "
                             "phase")
    parser.add_argument("-m", "--machine", dest="machine",
                        help="The name of the machine for loading machine-"
                             "related config options", metavar="MACH")
    parser.add_argument("--polar_regions", dest="polar_regions",
                        action='store_true',
                        help="Include config options for analysis focused on "
                             "polar regions")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    config = MpasConfigParser()

    # add default.cfg to cover default not included in the config files
    # provided on the command line
    config.add_from_package('mpas_analysis', 'default.cfg')

    # Add config options for E3SM supported machines from the mache package
    machine = args.machine

    if machine is None and 'E3SMU_MACHINE' in os.environ:
        machine = os.environ['E3SMU_MACHINE']

    if machine is None:
        machine = discover_machine()

    if machine is not None:
        print(f'Detected E3SM supported machine: {machine}')
        config.add_from_package('mache.machines', f'{machine}.cfg')
        try:
            config.add_from_package('mpas_analysis.configuration',
                                    f'{machine}.cfg')
        except FileNotFoundError:
            # we don't have a config file for this machine, so we'll just
            # skip it.
            print(f'Warning: no MPAS-Analysis config file found for machine:'
                  f' {machine}')
            pass

    if args.polar_regions:
        config.add_from_package('mpas_analysis', 'polar_regions.cfg')

    if machine is not None:
        # set the username so we can use it in the htmlSubdirectory
        machine_info = MachineInfo(machine=machine)
        config.set('web_portal', 'username', machine_info.username)

    shared_configs = config.list_files()

    for user_config in args.config_file:
        if not os.path.exists(user_config):
            raise OSError(f'Config file {user_config} not found.')

        config.add_user_config(user_config)

    print('Using the following config files:')
    for config_file in config.list_files():
        print(f'   {config_file}')

    if args.list:
        # set this config option so we don't have issues
        config.set('diagnostics', 'baseDirectory', '')
        analyses = build_analysis_list(config, control_config=None)
        for analysisTask in analyses:
            print('task: {}'.format(analysisTask.taskName))
            print('    component: {}'.format(analysisTask.componentName)),
            print('    tags: {}'.format(', '.join(analysisTask.tags)))
        sys.exit(0)

    if args.plot_colormaps:
        register_custom_colormaps()
        _plot_color_gradients()
        sys.exit(0)

    if config.has_option('runs', 'controlRunConfigFile'):
        control_config_file = config.get('runs', 'controlRunConfigFile')
        if not os.path.exists(control_config_file):
            raise OSError('A control config file {} was specified but the '
                          'file does not exist'.format(control_config_file))

        control_config = MpasConfigParser()
        for config_file in shared_configs:
            if config_file.endswith('.py'):
                # we'll skip config options set in python files
                continue
            control_config.add_from_file(config_file)
        control_config.add_user_config(control_config_file)

        # replace the log directory so log files get written to this run's
        # log directory, not the control run's
        logs_dir = build_config_full_path(config, 'output', 'logsSubdirectory')

        control_config.set('output', 'logsSubdirectory', logs_dir)

        print('Comparing to control run {} rather than observations. \n'
              'Make sure that MPAS-Analysis has been run previously with the '
              'control config file.'.format(control_config.get('runs',
                                                               'mainRunName')))
    else:
        control_config = None

    components = ['ocean', 'seaIce']

    if args.purge:
        purge_output(config, components)

    if config.has_option('runs', 'mainRunConfigFile'):
        symlink_main_run(config, components)

    if args.generate:
        update_generate(config, args.generate)

    if control_config is not None:
        # we want to use the "generate" option from the current run, not
        # the control config file
        control_config.set('output', 'generate', config.get('output',
                                                            'generate'))

    log_dir = build_config_full_path(config, 'output', 'logsSubdirectory')
    make_directories(log_dir)

    file_cache_maxsize = config.getint('input', 'file_cache_maxsize')
    try:
        xarray.set_options(file_cache_maxsize=file_cache_maxsize)
    except ValueError:
        # xarray version doesn't support file_cache_maxsize yet...
        pass

    start_time = time.time()

    plots_directory = build_config_full_path(config, 'output',
                                             'plotsSubdirectory')
    make_directories(plots_directory)

    html_base_directory = build_config_full_path(config, 'output',
                                                 'htmlSubdirectory')
    make_directories(html_base_directory)
    for config_filename in args.config_file:
        config_filename = os.path.abspath(config_filename)
        print(f'copying {config_filename} to HTML dir.')
        basename = os.path.basename(config_filename)
        copyfile(config_filename, f'{html_base_directory}/{basename}')

    analysis_list = build_analysis_list(config, control_config)
    analyses = determine_analyses_to_generate(analysis_list)
    setup_analysis(analyses, config, components, args.verbose)

    setup_duration = time.time() - start_time

    if not args.setup_only and not args.html_only:
        run_analysis(config, analyses)
        run_duration = time.time() - start_time
        m, s = divmod(setup_duration, 60)
        h, m = divmod(int(m), 60)
        print('Total setup time: {}:{:02d}:{:05.2f}'.format(h, m, s))
        m, s = divmod(run_duration, 60)
        h, m = divmod(int(m), 60)
        print('Total run time: {}:{:02d}:{:05.2f}'.format(h, m, s))

    if not args.setup_only:
        generate_html(config, analyses, control_config, args.config_file)


if __name__ == "__main__":
    main()
