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

from multiprocessing import Process, Value
import time
import traceback
import logging
import sys

from mpas_analysis.shared.io.utility import build_config_full_path


class AnalysisTask(Process):
    """
    The base class for analysis tasks.

    Attributes
    ----------
    config : mpas_tools.config.MpasConfigParser
        Contains configuration options

    taskName : str
        The name of the task, typically the same as the class name except
        starting with lowercase (e.g. 'myTask' for class 'MyTask')

    componentName : {'ocean', 'seaIce'}
        The name of the component

    tags : list of str
        Tags used to describe the task (e.g. 'timeSeries', 'climatology',
        horizontalMap', 'index', 'transect').  These are used to determine
        which tasks are generated (e.g. 'all_transect' or 'no_climatology'
        in the 'generate' flags)

    runAfterTasks : list
        tasks that must be complete before this task can run

    downstreamTasks : set
        tuples of task and subtask names indicating what tasks depend on this
        task, used to remove those tasks when this one fails during setup

    subtasks : dict
        Subtasks of this task, with subtask names as keys

    streamNames : list
        A list of MPAS stream names used by this task

    plotsDirectory : str
        The directory for writing plots (which is also created if it doesn't
        exist)

    namelists : dict
        Namelist options for each valid input section in the config file

    restartFile : str
        The name of a restart file that was found in the run directory,
        often used for mesh information but also useful for determining the
        simulation start time

    historyFiles : dict
        A nested dictionary.  The outer keys are each of the ``stream_names``.
        The inner keys are:

        - ``files`` - the input files for the stream

        - ``years``, ``months``, ``days`` - a year, month and day taken from
          each file name in ``files``.

    anomalyRefYears : dict
        For each type of analysis (climatology, time series, and climate
        index) supported by the component, the anomaly reference year either
        from a config option or the start data of the simulation

    calendar : {'gregorian', 'gregorian_noleap'}
        The calendar used in the MPAS run

    xmlFileNames : list of strings
        The XML file associated with each plot produced by this analysis, empty
        if no plots were produced

    logger : ``logging.Logger``
        A logger for output during the run phase of an analysis task
    """
    # Authors
    # -------
    # Xylar Asay-Davis

    # flags for run status
    UNSET = 0
    READY = 1
    BLOCKED = 2
    RUNNING = 3
    SUCCESS = 4
    FAIL = 5

    def __init__(self, config, taskName, componentName, tags=None,
                 subtaskName=None, streamNames=None):
        """
        Construct the analysis task.

        Individual tasks (children classes of this base class) should first
        call this method to perform basic initialization, then, define the
        ``taskName``, ``componentName`` and list of ``tags`` for the task.

        Parameters
        ----------
        config :  mpas_tools.config.MpasConfigParser
            Contains configuration options

        taskName :  str
            The name of the task, typically the same as the class name except
            starting with lowercase (e.g. 'myTask' for class 'MyTask')

        componentName :  {'ocean', 'seaIce'}
            The name of the component (same as the folder where the task
            resides)

        tags :  list of str, optional
            Tags used to describe the task (e.g. 'timeSeries', 'climatology',
            horizontalMap', 'index', 'transect').  These are used to determine
            which tasks are generated (e.g. 'all_transect' or 'no_climatology'
            in the 'generate' flags)

        subtaskName : str, optional
            If this is a subtask of ``taskName``, the name of the subtask

        streamNames : list
            A list of MPAS stream names used by this task
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        if subtaskName is None:
            self.fullTaskName = taskName
            self.printTaskName = taskName
        else:
            self.fullTaskName = '{}_{}'.format(taskName, subtaskName)
            self.printTaskName = '{}: {}'.format(taskName, subtaskName)

        # call the constructor from the base class (Process)
        super(AnalysisTask, self).__init__(name=self.fullTaskName)

        self.config = config
        self.taskName = taskName
        self.subtaskName = subtaskName
        self.componentName = componentName
        if tags is None:
            self.tags = []
        else:
            self.tags = tags
        if streamNames is None:
            self.streamNames = []
        else:
            self.streamNames = streamNames
        self.subtasks = []
        self.logger = None
        self.runAfterTasks = []
        self.downstreamTasks = set()
        self.xmlFileNames = []

        # initialized during setup and check
        self.plotsDirectory = None
        self.namelists = None
        self.restartFile = None
        self.historyFiles = None
        self.anomalyRefYears = None
        self.calendar = None

        # non-public attributes related to multiprocessing and logging
        self.daemon = True
        self._runStatus = Value('i', AnalysisTask.UNSET)
        self._stackTrace = None
        self._logFileName = None

        # the number of subprocesses run by this process, typically 1 but
        # could be 12 for ncclimo in bck or mpi mode
        self.subprocessCount = 1

        # run the task directly as opposed to launching it as a new process
        # even in parallel because it has subprocesses such as Pools
        self.runDirectly = False

    def setup_and_check(self):
        """
        Perform steps to set up the analysis (e.g. reading namelists and
        streams files). Check to make sure the MPAS simulation was configured
        to support this analysis.  Raise an exception if not.
        """
        pass

    def run_task(self):
        """
        Run the analysis.  Each task should override this function to do the
        work of computing and/or plotting analysis
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        return

    def run_after(self, task):
        """
        Only run this task after the given task has completed.  This allows a
        task to be constructed of multiple subtasks, some of which may block
        later tasks, while allowing some subtasks to run in parallel.  It also
        allows for tasks to depend on other tasks (e.g. for computing
        climatologies or extracting time series for many variables at once).

        Parameters
        ----------
        task : mpas_analysis.shared.AnalysisTask
            The task that should finish before this one begins
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        if task not in self.runAfterTasks:
            self.runAfterTasks.append(task)
            task.downstreamTasks.add((self.taskName, self.subtaskName))

    def add_subtask(self, subtask):
        """
        Add a subtask to this tasks.  This task always runs after the subtask
        has finished.  However, this task gets set up *before* the subtask,
        so the setup of the subtask can depend on fields defined during the
        setup of this task (the parent).

        Parameters
        ----------
        subtask : ``AnalysisTask``
            The subtask to run as part of this task
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        if subtask not in self.subtasks:
            self.subtasks.append(subtask)
            subtask.downstreamTasks.add((self.taskName, self.subtaskName))

    def run(self, writeLogFile=True):
        """
        Sets up logging and then runs the analysis task.

        Parameters
        ----------
        writeLogFile : bool, optional
            If ``True``, output to stderr and stdout get written to a log file.
            Otherwise, the internal logger ``self.logger`` points to stdout
            and no log file is created.  The intention is for logging to take
            place in parallel mode but not in serial mode.
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # redirect output to a log file
        if writeLogFile:
            self.logger = logging.getLogger(self.fullTaskName)
            handler = logging.FileHandler(self._logFileName)
        else:
            self.logger = logging.getLogger()
            handler = logging.StreamHandler(sys.stdout)

        formatter = AnalysisFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if writeLogFile:
            oldStdout = sys.stdout
            oldStderr = sys.stderr
            sys.stdout = StreamToLogger(self.logger, logging.INFO)
            sys.stderr = StreamToLogger(self.logger, logging.ERROR)

        startTime = time.time()
        try:
            self.run_task()
            self._runStatus.value = AnalysisTask.SUCCESS
        except (Exception, BaseException) as e:
            if isinstance(e, KeyboardInterrupt):
                raise e
            self._stackTrace = traceback.format_exc()
            self.logger.error("analysis task {} failed during run \n"
                              "{}".format(self.fullTaskName, self._stackTrace))
            self._runStatus.value = AnalysisTask.FAIL

        runDuration = time.time() - startTime
        m, s = divmod(runDuration, 60)
        h, m = divmod(int(m), 60)
        self.logger.info('Execution time: {}:{:02d}:{:05.2f}'.format(h, m, s))

        if writeLogFile:
            handler.close()
            # restore stdout and stderr
            sys.stdout = oldStdout
            sys.stderr = oldStderr

        # remove the handlers from the logger (probably only necessary if
        # writeLogFile==False)
        self.logger.handlers = []

    def check_generate(self):

        """
        Determines if this analysis should be generated, based on the
        ``generate`` config option and ``taskName``, ``componentName`` and
        ``tags``.

        Individual tasks do not need to create their own versions of this
        function.

        Returns
        -------
        generate : bool
            Whether or not this task should be run.

        Raises
        ------
        ValueError : If one of ``self.taskName``, ``self.componentName``
            or ``self.tags`` has not been set.
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        for memberName in ['taskName', 'componentName', 'tags']:
            if not hasattr(self, memberName):
                raise ValueError('Analysis tasks must define self.{} in their '
                                 '__init__ method.'.format(memberName))

        if (not isinstance(self.tags, list) and
                self.tags is not None):
            raise ValueError('Analysis tasks\'s member self.tags '
                             'must be None or a list of strings.')

        config = self.config
        generateList = config.getexpression('output', 'generate')
        if len(generateList) > 0 and generateList[0][0:5] == 'only_':
            # add 'all' if the first item in the list has the 'only' prefix.
            # Otherwise, we would not run any tasks
            generateList = ['all'] + generateList
        generate = False
        for element in generateList:
            if '_' in element:
                (prefix, suffix) = element.split('_', 1)
            else:
                prefix = element
                suffix = None

            allSuffixes = [self.componentName]
            if self.tags is not None:
                allSuffixes = allSuffixes + self.tags
            noSuffixes = [self.taskName] + allSuffixes
            if prefix == 'all':
                if (suffix in allSuffixes) or (suffix is None):
                    generate = True
            elif prefix == 'no':
                if suffix in noSuffixes:
                    generate = False
            if prefix == 'only':
                if suffix not in allSuffixes:
                    generate = False
            elif element == self.taskName:
                generate = True

        return generate

    def check_analysis_enabled(self, analysisOptionName, default=False,
                               raiseException=True):
        """
        Check to make sure a given analysis is turned on, issuing a warning or
        raising an exception if not.

        Parameters
        ----------
        analysisOptionName : str
            The name of a boolean namelist option indicating whether the given
            analysis member is enabled

        default : bool, optional
            If no analysis option with the given name can be found, indicates
            whether the given analysis is assumed to be enabled by default.

        raiseException : bool, optional
            Whether

        Returns
        -------
        enabled : bool
            Whether the given analysis is enabled

        Raises
        ------
        RuntimeError
            If the given analysis option is not found and ``default`` is not
            ``True`` or if the analysis option is found and is ``False``.  The
            exception is only raised if ``raiseException = True``.
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        if len(self.namelists) == 0:
            raise IOError(f'No namelists were found for {self.printTaskName}')

        all_enabled = True
        for namelist in self.namelists.values():
            try:
                optionName = analysisOptionName
                enabled = namelist.getbool(optionName)
            except ValueError:
                enabled = default
                if default:
                    print(f'Warning: namelist option {analysisOptionName} not '
                          f'found.\n'
                          f'This likely indicates that the simulation you '
                          f'are analyzing was run with an\n'
                          f'older version of MPAS-O that did not support '
                          f'this flag.  Assuming enabled.')

            if not enabled and raiseException:
                raise RuntimeError('*** MPAS-Analysis relies on {} = .true.\n'
                                   '*** Make sure to enable this analysis '
                                   'member.'.format(analysisOptionName))
            all_enabled = all_enabled and enabled

        return all_enabled

    def framework_setup(self, namelists, restartFile, historyFiles,
                        anomalyRefYears):
        """
        Used by the MPAS-Analysis framework to set attributes shared among all
        tasks from a given component as well as creating the plot directory
        and determining a log file for this task
        """
        self.namelists = namelists
        self.restartFile = restartFile
        self.historyFiles = {}
        # make available only the streams that this task uses, mostly as a
        # sanity check that the task actually asked for the streams it will
        # use.
        for streamName in self.streamNames:
            self.historyFiles[streamName] = historyFiles[streamName]
        self.anomalyRefYears = anomalyRefYears
        self.calendar = namelists['input'].get('config_calendar_type')

        self.plotsDirectory = build_config_full_path(self.config, 'output',
                                                     'plotsSubdirectory')

        # redirect output to a log file
        logsDirectory = build_config_full_path(self.config, 'output',
                                               'logsSubdirectory')

        self._logFileName = '{}/{}.log'.format(logsDirectory,
                                               self.fullTaskName)

    def get_history_files(self, streamName, startYear=None, endYear=None,
                          analysisType=None, anomalyRefYear=None):
        """
        Get a list of file names from the given stream, optionally within the
        given time range

        Parameters
        ----------
        streamName : str
            The name of a stream that the files were output from

        startYear, endYear : int, optional
            The range of years to restrict the files to

        analysisType : str, optional
            Type of analysis that the history files will be used for
            (typically one or more of "climatology", "timeSeries" and "index"),
            used here to determine the start and end years from config options

        anomalyRefYear : int, optional
            A reference year from which to take anomalies.  Files (and years,
            months and days) will be included from this year.

        Returns
        -------
        fileNames : list
            A list of files from the stream in the given range of years

        years, months, days : list
            A list of years, months and days for the date of each file
        """
        historyDict = self.historyFiles[streamName]
        fileNames = historyDict['files']
        years = historyDict['years']
        months = historyDict['months']
        days = historyDict['days']
        if analysisType is not None:
            startYear = self.config.getint(analysisType, 'startYear')
            endYear = self.config.getint(analysisType, 'endYear')

        if startYear is not None or endYear is not None:
            years = historyDict['years']
            if startYear is None:
                startYear = years[0]
            if endYear is None:
                endYear = years[-1]

            if anomalyRefYear is not None:
                indices = [index for index in range(len(years)) if
                           (startYear <= years[index] <= endYear or
                            years[index] == anomalyRefYear)]
            else:
                indices = [index for index in range(len(years)) if
                             startYear <= years[index] <= endYear]
            fileNames = fileNames[indices]
            years = years[indices]
            months = months[indices]
            days = days[indices]

        return fileNames, years, months, days


class AnalysisFormatter(logging.Formatter):
    """
    A custom formatter for logging

    Modified from:
    https://stackoverflow.com/a/8349076/7728169
    """
    # Authors
    # -------
    # Xylar Asay-Davis

    # printing error messages without a prefix because they are sometimes
    # errors and sometimes only warnings sent to stderr
    dbg_fmt = "DEBUG: %(module)s: %(lineno)d: %(msg)s"
    info_fmt = "%(msg)s"
    err_fmt = info_fmt

    def __init__(self, fmt=info_fmt):
        logging.Formatter.__init__(self, fmt)

    def format(self, record):

        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._fmt

        # Replace the original format with one customized by logging level
        if record.levelno == logging.DEBUG:
            self._fmt = AnalysisFormatter.dbg_fmt

        elif record.levelno == logging.INFO:
            self._fmt = AnalysisFormatter.info_fmt

        elif record.levelno == logging.ERROR:
            self._fmt = AnalysisFormatter.err_fmt

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._fmt = format_orig

        return result


class StreamToLogger(object):
    """
    Modified based on code by:
    https://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/

    Copyright (C) 2011 Ferry Boender

    License: "available under the GPL" (the author does not provide more
    details)

    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, str(line.rstrip()))

    def flush(self):
        pass
