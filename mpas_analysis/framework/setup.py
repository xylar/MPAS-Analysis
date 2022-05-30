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

import os
import shutil
import sys
import traceback

from mpas_tools.config import MpasConfigParser

from mpas_analysis.shared.io.utility import build_config_full_path, \
    make_directories

from mpas_analysis.framework.input import get_namelist_restart_history_files


def purge_output(config, components):
    """
    Remove directories in the output path so the analysis can be rerun
    completely.

    Parameters
    ----------
    config : mpas_tools.config.MpasConfigParser
        contains config options

    components : list
        A list of the components to set up ("ocean" and/or "seaIce")
    """
    output_directory = config.get('output', 'baseDirectory')
    if not os.path.exists(output_directory):
        print(f'Output directory {output_directory} does not exist.\n'
              f'No purge necessary.')
    else:
        for subdirectory in ['input', 'plots', 'logs', 'mpasClimatology',
                             'mapping', 'timeSeries', 'html', 'mask',
                             'profiles']:
            option = f'{subdirectory}Subdirectory'
            directory = build_config_full_path(
                config=config, section='output',
                relativePathOption=option)
            if os.path.exists(directory):
                print(f'Deleting contents of {directory}')
                if os.path.islink(directory):
                    os.unlink(directory)
                else:
                    shutil.rmtree(directory)

        for component in components:
            for subdirectory in ['climatology', 'remappedClim']:
                option = f'{subdirectory}Subdirectory'
                section = f'{component}Observations'
                directory = build_config_full_path(
                    config=config, section='output',
                    relativePathOption=option,
                    relativePathSection=section)
                if os.path.exists(directory):
                    print(f'Deleting contents of {directory}')
                    if os.path.islink(directory):
                        os.unlink(directory)
                    else:
                        shutil.rmtree(directory)


def symlink_main_run(config, components,
                     subdirectories=('mpasClimatology', 'timeSeries',
                                     'mapping', 'mask', 'profiles')):
    """
    Create symlinks to the climatology and time-series directories for the
    main run that has already been computed so we don't have to recompute
    the analysis.

    Parameters
    ----------
    config : mpas_tools.config.MpasConfigParser
        contains config options

    components : list
        A list of the components to set up ("ocean" and/or "seaIce")

    subdirectories : tuple
        A list of subdirectories to link from the main run
    """

    main_config_file = config.get('runs', 'mainRunConfigFile')
    if not os.path.exists(main_config_file):
        raise OSError(f'A main config file {main_config_file} was specified '
                      f'but the file does not exist')
    main_config = MpasConfigParser()
    main_config.add_from_package('mpas_analysis', 'default.cfg')
    main_config.add_user_config(main_config_file)

    for subdirectory in subdirectories:
        section = 'output'
        option = f'{subdirectory}Subdirectory'
        _link_dir(config=config, main_config=main_config, section=section,
                  option=option)

    for component in components:
        for subdirectory in ['climatology', 'remappedClim']:
            section = f'{component}Observations'
            option = f'{subdirectory}Subdirectory'
            _link_dir(config=config, main_config=main_config, section=section,
                      option=option)


def update_generate(config, generate):
    """
    Update the 'generate' config option using a string from the command line.

    Parameters
    ----------
    config : mpas_tools.config.MpasConfigParser
        contains config options

    generate : str
        a comma-separated string of generate flags: either names of analysis
        tasks or commands of the form ``all_<tag>`` or ``no_<tag>`` indicating
        that analysis with a given tag should be included or excluded).
    """

    # overwrite the 'generate' in config with a string that parses to
    # a list of string
    generate_list = generate.split(',')
    generate_string = ', '.join(["'{}'".format(element)
                                for element in generate_list])
    generate_string = '[{}]'.format(generate_string)
    config.set('output', 'generate', generate_string)


def determine_analyses_to_generate(analyses):
    """
    Build a list of analysis tasks to run based on the 'generate' config
    option (or command-line flag) and prerequisites and subtasks of each
    requested task.

    Parameters
    ----------
    analyses : list
        A list of all analysis tasks

    Returns
    -------
    analyses_to_generate :  dict
        A dictionary of analysis tasks to run with tuples of task and subtask
        names as keys
    """

    analyses_to_generate = dict()
    # check which analysis we actually want to generate and only keep those
    for analysisTask in analyses:
        # update the dictionary with this task and perhaps its subtasks
        _add_task_and_subtasks(analysisTask, analyses_to_generate)

    return analyses_to_generate


def setup_analysis(analyses, config, components, verbose):
    """
    Set up each analysis task, including calling its ``framework_setup()`` and
    ``setup_and_check()`` methods.  Any tasks that raise exceptions during
    setup will be removed, along with any tasks that depend on them

    Parameters
    ----------
    analyses : dict
        A dictionary of analysis tasks to run with tuples of task and subtask
        names as keys

    config : mpas_tools.config.MpasConfigParser
        contains config options

    components : list
        A list of the components to set up ("ocean" and/or "seaIce")

    verbose : bool
        Whether to write out a full stack trace when exceptions occur during
        ``setup_and_check()`` calls for each task
    """
    possible_analysis_types = {
        'ocean': ['climatology', 'timeSeries', 'index'],
        'seaIce': ['climatology', 'timeSeries']}

    skip_time_bounds = {
        'ocean': ['meridionalHeatTransportOutput',
                  'eddyProductVariablesOutput'],
        'seaIce': []
    }

    for component in components:
        stream_names, analysis_types = \
            _determine_component_streams_and_analysis_types(
                component, analyses, possible_analysis_types[component])
        namelists, restart_file, history_files, anomaly_ref_years = \
            get_namelist_restart_history_files(
                config, component, stream_names,
                time_bounds_sections=analysis_types,
                skip_time_bounds=skip_time_bounds[component])

        for task in analyses.values():
            if task.componentName == component:
                task.framework_setup(namelists, restart_file, history_files,
                                     anomaly_ref_years)

    _setup_and_check_analyses(analyses, verbose)


def _add_task_and_subtasks(task, analyses, call_check_generate=True):

    """
    If a task has been requested through the generate config option or
    if it is a prerequisite of a requested task, add it to the dictionary of
    tasks to generate.

    Parameters
    ----------
    task : mpas_analysis.shared.AnalysisTask
        A task to be added

    analyses : dict
        The list of analysis tasks to be generated, which this call may
        update to include this task and its subtasks

    call_check_generate : bool, optional
        Whether the ``check_generate`` method should be call for this task to
        see if it has been requested.  We skip this for subtasks and
        prerequisites, since they are needed by another task regardless of
        whether the user specifically requested them.
    """

    key = (task.taskName, task.subtaskName)
    if key in analyses.keys():
        # The task was already added
        return

    # for each analysis task, check if we want to generate this task
    # and if the analysis task has a valid configuration
    if call_check_generate and not task.check_generate():
        # we don't need to add this task -- it wasn't requested
        return

    # first, we should try to add the prerequisites of this task and its
    # subtasks (if they aren't also subtasks for this task)
    prereqs = task.runAfterTasks
    for subtask in task.subtasks:
        for prereq in subtask.runAfterTasks:
            if prereq not in task.subtasks:
                prereqs.extend(subtask.runAfterTasks)

    for prereq in prereqs:
        _add_task_and_subtasks(prereq, analyses, call_check_generate=False)

    # next, we should try to add the subtasks.  This is done after the current
    # analysis task has been set up in case subtasks depend on information
    # from the parent task
    for subtask in task.subtasks:
        _add_task_and_subtasks(subtask, analyses, call_check_generate=False)

    analyses[key] = task


def _determine_component_streams_and_analysis_types(component, analyses,
                                                    possible_analysis_types):
    """
    Get the names of the streams and the types of analysis used by the
    requested analysis tasks from a component

    Parameters
    ----------
    component : {'ocean', 'sea_ice'}
        The name of the component (same as the folder where the task
        resides)

    analyses : dict
        A dictionary of analysis tasks to run with tuples of task and subtask
        names as keys

    possible_analysis_types : list
        A list of types of analysis to generate (typically one or more of
        "climatology", "timeSeries" and "index")

    Returns
    -------
    stream_names : set
        The set of stream names needed by the requested analysis tasks

    analysis_types : set
        The set of ``possible_analysis_types`` actually used in the requested
        analysis tasks
    """
    stream_names = set()
    analysis_types = set()

    for task in analyses.values():
        if task.componentName != component:
            continue
        for stream_name in task.streamNames:
            stream_names.add(stream_name)

        for analysis_type in possible_analysis_types:
            if analysis_type in task.tags:
                analysis_types.add(analysis_type)

    return stream_names, analysis_types


def _setup_and_check_analyses(analyses, verbose):
    """
    Call each task's ``setup_and_check()`` method, removing any tasks that
    fail as well as tasks that depend on them.

    Parameters
    ----------
    analyses : dict
        A dictionary of analysis tasks to run with tuples of task and subtask
        names as keys

    verbose : bool
        Whether to write out a full stack trace when exceptions occur during
        ``setup_and_check()`` calls for each task
    """

    failures = 0

    print('')

    analysis_keys = list(analyses.keys())
    # check which analysis we actually want to generate and only keep those
    for key in analysis_keys:
        if key in analyses:
            # this task is still in analyses (hasn't been removed due to
            # failures)
            analysis_task = analyses[key]
            removed = _add_setup_and_check_task(analysis_task, analyses,
                                                verbose)

            failures += removed

    if failures > 0:
        print(f'\n{failures} tasks and subtasks failed during setup.')
        if not verbose:
            print('To find out why these tasks are failing, use the --verbose '
                  'flag')

    print('')


def _add_setup_and_check_task(task, analyses, verbose):

    """
    Call the ``setup_and_check()`` method for the analysis task, removing it
    and its downstream tasks (those that depend on it) if the check fails.

    Parameters
    ----------
    task : mpas_analysis.shared.AnalysisTask
        A task to be set up and checked

    analyses : dict
        The list of analysis tasks to be generated, which this call may
        update to include this task and its subtasks

    verbose : bool
        Whether to write out a full stack trace when exceptions occur during
        ``setup_and_check()`` calls for each task

    Returns
    -------
    removed : int
        The number of tasks that were removed due to setup failures
    """

    try:
        task.setup_and_check()
    except (Exception, BaseException):
        if verbose:
            traceback.print_exc(file=sys.stdout)
        print(f"Warning: {task.printTaskName} failed during check and will "
              f"not be run")
        key = (task.taskName, task.subtaskName)
        removed = _remove_task_and_downstream(key, analyses, warn=False)
        return removed

    return 0


def _remove_task_and_downstream(key, analyses, warn):

    """
    If a task has been requested through the generate config option or
    if it is a prerequisite of a requested task, add it to the dictionary of
    tasks to generate.

    Parameters
    ----------
    key : tuple
        The task and subtask name for the task to remove

    analyses : dict
        The list of analysis tasks to be generated, which this call may
        update to include this task and its subtasks

    warn : bool
        Whether to print a warning message about the removed analysis task
    """
    removed = 0
    if key not in analyses:
        return removed
    task = analyses.pop(key)
    removed += 1
    if warn:
        print(f"Warning: prerequisite of {task.printTaskName} failed during "
              f"check, so this task will not be run")
    for other_key in task.downstreamTasks:
        removed += _remove_task_and_downstream(other_key, analyses, warn=True)
    return removed


def _link_dir(config, main_config, section, option):
    dest_directory = build_config_full_path(
        config=config, section='output', relativePathOption=option,
        relativePathSection=section)
    if not os.path.exists(dest_directory):

        source_directory = build_config_full_path(
            config=main_config, section='output', relativePathOption=option,
            relativePathSection=section)

        if os.path.exists(source_directory):

            dest_base, _ = os.path.split(dest_directory)

            make_directories(dest_base)

            os.symlink(source_directory, dest_directory)
