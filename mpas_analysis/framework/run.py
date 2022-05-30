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

import sys
import progressbar
import logging

from mpas_analysis.shared.analysis_task import AnalysisFormatter

from mpas_analysis.shared.io.utility import build_config_full_path

from mpas_analysis.shared import AnalysisTask


def run_analysis(config, analyses):
    """
    Run all the tasks, either in serial or in parallel

    Parameters
    ----------
    config : mpas_tools.config.MpasConfigParser
        contains config options

    analyses : dict
        A dictionary of analysis tasks to run with (task, subtask) names as
        keys
    """

    # write the config file the log directory
    logs_directory = build_config_full_path(config, 'output',
                                            'logsSubdirectory')

    main_run_name = config.get('runs', 'mainRunName')
    if main_run_name == '<<<placeholder>>>':
        raise ValueError('You must supply the config option "mainRunName"')

    for section in ['input', 'output']:
        base_directory = config.get(section, 'baseDirectory')
        if base_directory == '<<<placeholder>>>':
            raise ValueError(f'You must supply the config option '
                             f'"baseDirectory" in section [{section}]')

    if len(main_run_name) > 55:
        print(f'Warning: The main run name is quite long and will be '
              f'truncated in some plots: \n{main_run_name}\n\n')

    config_file_name = f'{logs_directory}/{main_run_name}.cfg'

    with open(config_file_name, 'w') as config_file:
        config.write(config_file)

    parallel_task_count = config.getint('execute', 'parallelTaskCount')

    is_parallel = parallel_task_count > 1 and len(analyses) > 1

    for task in analyses.values():
        if not task.runAfterTasks and not task.subtasks:
            task._runStatus.value = AnalysisTask.READY
        else:
            task._runStatus.value = AnalysisTask.BLOCKED

    tasks_with_errors = []
    running_tasks = {}

    # redirect output to a log file
    logs_directory = build_config_full_path(config, 'output',
                                            'logsSubdirectory')

    log_file_name = '{}/taskProgress.log'.format(logs_directory)

    logger = logging.getLogger('mpas_analysis')
    handler = logging.FileHandler(log_file_name)

    formatter = AnalysisFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    total_task_count = len(analyses)
    widgets = ['Running tasks: ', progressbar.Percentage(), ' ',
               progressbar.Bar(), ' ', progressbar.ETA()]
    progress = progressbar.ProgressBar(widgets=widgets,
                                       max_value=total_task_count).start()

    running_process_count = 0

    # run each analysis task
    while True:
        # we still have tasks to run
        for task in analyses.values():
            if task._runStatus.value == AnalysisTask.BLOCKED:
                prereqs = task.runAfterTasks + task.subtasks
                prereq_status = [prereq._runStatus.value for prereq in prereqs]
                if any([runStatus == AnalysisTask.FAIL for runStatus in
                        prereq_status]):
                    # a prerequisite failed so this task cannot succeed
                    task._runStatus.value = AnalysisTask.FAIL
                if all([runStatus == AnalysisTask.SUCCESS for runStatus in
                        prereq_status]):
                    # no unfinished prerequisites so we can run this task
                    task._runStatus.value = AnalysisTask.READY

        unfinished_count = 0
        for task in analyses.values():
            if task._runStatus.value not in [AnalysisTask.SUCCESS,
                                             AnalysisTask.FAIL]:
                unfinished_count += 1

        progress.update(total_task_count - unfinished_count)

        if unfinished_count <= 0 and running_process_count == 0:
            # we're done
            break

        # launch new tasks
        run_directly = False
        task = None
        for key, task in analyses.items():
            if task._runStatus.value == AnalysisTask.READY:
                if is_parallel:
                    new_process_count = running_process_count + \
                        task.subprocessCount
                    if new_process_count > parallel_task_count and \
                            running_process_count > 0:
                        # this task should run next but we need to wait for
                        # more processes to finish
                        break

                    logger.info('Running {}'.format(
                        task.printTaskName))
                    if task.run_directly:
                        task.run(writeLogFile=True)
                        run_directly = True
                        break
                    else:
                        task._runStatus.value = AnalysisTask.RUNNING
                        task.start()
                        running_tasks[key] = task
                        running_process_count = new_process_count
                        if running_process_count >= parallel_task_count:
                            # don't try to run any more tasks
                            break
                else:
                    task.run(writeLogFile=False)
                    break

        if is_parallel:

            if not run_directly:
                assert(running_process_count > 0)
                # wait for a task to finish
                task = _wait_for_task(running_tasks)
                key = (task.taskName, task.subtaskName)
                running_tasks.pop(key)
                running_process_count -= task.subprocessCount

            task_title = task.printTaskName

            if task._runStatus.value == AnalysisTask.SUCCESS:
                logger.info("   Task {} has finished successfully.".format(
                    task_title))
            elif task._runStatus.value == AnalysisTask.FAIL:
                message = f"ERROR in task {task_title}.  See log file " \
                          f"{task._logFileName} for details"
                logger.error(message)
                print(message)
                tasks_with_errors.append(task_title)
            else:
                message = "Unexpected status from in task {task_title}.  This " \
                          "may be a bug."
                logger.error(message)
                print(message)
        else:
            if task._runStatus.value == AnalysisTask.FAIL:
                sys.exit(1)

    progress.finish()

    # blank line to make sure remaining output is on a new line
    print('')

    handler.close()
    logger.handlers = []

    # raise the last exception so the process exits with an error
    error_count = len(tasks_with_errors)
    if error_count == 1:
        print("There were errors in task {}".format(tasks_with_errors[0]))
        sys.exit(1)
    elif error_count > 0:
        print("There were errors in {} tasks: {}".format(
            error_count, ', '.join(tasks_with_errors)))
        print("See log files in {} for details.".format(logs_directory))
        print("The following commands may be helpful:")
        print("  cd {}".format(logs_directory))
        print("  grep Error *.log")
        sys.exit(1)
    else:
        print('Log files for executed tasks can be found in {}'.format(
            logs_directory))


def _wait_for_task(running_tasks, timeout=0.1):
    """
    Build a list of analysis modules based on the 'generate' config option.
    New tasks should be added here, following the approach used for existing
    analysis tasks.

    Parameters
    ----------
    running_tasks : dict of ``AnalysisTasks``
        The tasks that are currently running, with task names as keys

    Returns
    -------
    task : ``AnalysisTasks``
        A task that finished
    """
    # Authors
    # -------
    # Xylar Asay-Davis

    # necessary to have a timeout so we can kill the whole thing
    # with a keyboard interrupt
    while True:
        for task in running_tasks.values():
            task.join(timeout=timeout)
            if not task.is_alive():
                return task
