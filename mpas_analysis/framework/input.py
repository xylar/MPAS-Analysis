import os
import xarray
import numpy
from datetime import datetime

from mpas_analysis.shared.io import NameList, StreamsFile
from mpas_analysis.shared.io.utility import build_config_full_path

from mpas_analysis.shared.io.utility import make_directories


def get_namelist_restart_history_files(config, component_name, stream_names,
                                       time_bounds_sections):
    """
    Get namelist, restart and history files for the given streams.  If
    necessary, the time bounds in the config file will be updated to match the
    dates of the available files.  The ``startDate`` and ``endDate`` config
    options will be set based on the start and end years in each
    ``time_bounds_sections``.

    Parameters
    ----------
    config : mpas_tools.config.MpasConfigParser
        Contains configuration options

    component_name : {'ocean', 'seaIce'}
        The name of the MPAS component

    stream_names : list
        A list of stream names that will be used in the analysis

    time_bounds_sections : list
        Sections in the config file with start and end years used to limit
        the range of output to process.  Typically, one or more of
        ['climatology', 'timeSeries', 'index'], depending on the component and
        the type of analysis to be run

    Returns
    -------
    namelists : dict
        Namelist options for each valid input section in the config file

    restart_file : str
        The name of a restart file that was found in the run directory,
        often used for mesh information but also useful for determining the
        simulation start time

    history_files : dict
        A nested dictionary.  The outer keys are each of the ``stream_names``.
        The inner keys are:

        - ``files`` - the input files for the stream

        - ``years``, ``months``, ``days`` - a year, month and day taken from
          each file name in ``files``.

    anomaly_ref_years : dict
        For each ``time_bounds_sections``, the anomaly reference year either
        from a config option or the start data of the simulation
    """
    base_directory = config.get('input', 'baseDirectory')
    if base_directory == '<<<placeholder>>>':
        raise ValueError('The base directory must be supplied for the [input]'
                         ' section')

    restart_file = None
    namelists = {}

    valid_input_sections = ['input']
    for input_sections in ['prev_input1', 'prev_input2']:
        base_directory = config.get(input_sections, 'baseDirectory')
        if base_directory != '<<<placeholder>>>':
            valid_input_sections.append(input_sections)

    for index in range(1, len(valid_input_sections)):
        prev_section = valid_input_sections[index-1]
        input_section = valid_input_sections[index]
        prev_start_year, _ = _get_start_and_end_year(
            config, prev_section, raise_error=True)
        _, end_year = _get_start_and_end_year(
            config, input_section, raise_error=True)
        if end_year >= prev_start_year:
            raise ValueError(f'The endYear in [{input_section}] must be before'
                             f' the startYear in [{prev_section}]')

    history_files = {}
    for stream_name in stream_names:
        history_files[stream_name] = {'files': [],
                                      'years': [],
                                      'months': [],
                                      'days': []}

    # iterate from newest to oldest
    for input_section in valid_input_sections[::-1]:
        namelist, run_streams,  history_streams = \
            _get_component_namelist_and_streams(
                config, component_name, input_section)

        namelists[input_section] = namelist

        try:
            restart_file = run_streams.readpath('restart')[0]
        except ValueError:
            restart_file = None

        calendar = namelist.get('config_calendar_type')

        start_year, end_year = _get_start_and_end_year(
            config, input_section)

        for stream_name in stream_names:
            input_files = _get_history_files(
                component_name, stream_name, start_year, end_year,
                calendar, history_streams)

            input_files = sorted(input_files)

            years, months, days = _get_files_year_month_day(
                input_files, history_streams, stream_name)

            symlink_files = _create_symlinks(
                    config, input_files, years, months, days, component_name,
                    stream_name)

            history_files[stream_name]['files'].extend(symlink_files)
            history_files[stream_name]['years'].extend(years)
            history_files[stream_name]['months'].extend(months)
            history_files[stream_name]['days'].extend(days)

    if restart_file is None:
        raise IOError('No MPAS restart file found: need at least one '
                      'restart file for analysis to work correctly')

    anomaly_ref_years = {}
    for time_bounds_section in time_bounds_sections:
        if config.has_option(time_bounds_section, 'anomalyRefYear'):
            anomaly_ref_year = \
                config.getint('climatology', 'anomalyRefYear')
        else:
            anomaly_ref_date = get_simulation_start_time(restart_file)
            anomaly_ref_year = int(anomaly_ref_date[0:4])
        anomaly_ref_years[time_bounds_section] = anomaly_ref_year

    for stream_name in stream_names:
        for time_bounds_section in time_bounds_sections:
            years = history_files[stream_name]['years']
            months = history_files[stream_name]['months']
            _update_time_bounds_from_file_names(
                config, time_bounds_section, years, months)

    return namelists, restart_file, history_files, anomaly_ref_years


def get_input_files_in_year_range(history_files, start_year, end_year):
    """
    Get input files in a range of years

    Parameters
    ----------
    history_files : dict
        The history files dictionary for a given stream, containing both file
        names and years, months and days for each file

    start_year : int
        The first year to include

    end_year : int
        The last year to include

    Returns
    -------
    input_files : list
        A list of file names within the range of years
    """
    years = history_files['years']
    input_files = history_files['files']
    indices = [index for index, year in enumerate(years) if
               start_year <= year <= end_year]
    input_files = input_files[indices]
    return input_files


def get_input_files_in_range(history_files, config, section):
    """
    Get input files in a range of years

    Parameters
    ----------
    history_files : dict
        The history files dictionary for a given stream, containing both file
        names and years, months and days for each file

    config : mpas_tools.config.MpasConfigParser
        Contains configuration options

    section : str
        The name of a config section containing "startYear" and "endYear"
        options to use to determine the range

    Returns
    -------
    input_files : list
        A list of file names within the range of years
    """
    start_year = config.getint(section, 'startYear')
    end_year = config.getint(section, 'endYear')
    get_input_files_in_year_range(history_files, start_year, end_year)


def get_simulation_start_time(restart_file):
    """
    Get the simulation start time from a restart file.

    Parameters
    ----------
    restart_file : str
        The name of a restart file from which to read the simulation start time

    Returns
    -------
    simulation_start_time : str
        The start date of the simulation
    """

    ds = xarray.open_dataset(restart_file)
    da = ds.simulationStartTime
    if da.dtype.type is numpy.string_:
        simulation_start_time = bytes.decode(da.values.tobytes())
    else:
        simulation_start_time = da.values.tobytes()
    # replace underscores so it works as a CF-compliant reference date
    simulation_start_time = \
        simulation_start_time.rstrip('\x00').replace('_', ' ')

    return simulation_start_time


def _get_component_namelist_and_streams(config, component_name, section):
    """
    Get the namelist and streams objects for this component
    """

    # read parameters from config file
    # the run directory contains the restart files
    run_directory = build_config_full_path(config, 'input', 'runSubdirectory')
    # if the history directory exists, use it; if not, fall back on
    # run_directory
    history_directory = build_config_full_path(
        config, section,
        f'{component_name}HistorySubdirectory',
        defaultPath=run_directory)

    namelist_file_name = build_config_full_path(
        config, section,
        f'{component_name}NamelistFileName')

    namelist = NameList(namelist_file_name)

    streams_file_name = build_config_full_path(
        config, section,
        f'{component_name}StreamsFileName')
    run_streams = StreamsFile(streams_file_name, streamsdir=run_directory)
    history_streams = StreamsFile(streams_file_name,
                                  streamsdir=history_directory)

    return namelist, run_streams, history_streams


def _get_start_and_end_year(config, section, raise_error=False):
    start_year = config.get(section, 'startYear')
    if start_year != '<<<placeholder>>>':
        start_year = int(start_year)
    else:
        start_year = None
    end_year = config.get(section, 'endYear')
    if end_year != '<<<placeholder>>>' and end_year != 'end':
        end_year = int(end_year)
    else:
        end_year = None

    if raise_error and start_year is None or end_year is None:
        raise ValueError(f'Expected valid startYear and endYear in config '
                         f'section [{section}]')

    return start_year, end_year


def _get_files_year_month_day(file_names, streams_file, stream_name):
    """
    Extract the year and month from file names associated with a stream

    Parameters
    ----------
    file_names : list of str
        The names of files with a year and month in their names.

    streams_file : mpas_analysis.shared.io.StreamsFile
        The parsed streams file, used to get a template for the

    stream_name : str
        The name of the stream with a file-name template for ``file_names``

    Returns
    -------
    years, months, days : list of int
        The years, months and days for each file in ``file_names``
    """

    template = streams_file.read_datetime_template(stream_name)
    template = os.path.basename(template)
    dts = [datetime.strptime(os.path.basename(file_name), template) for
           file_name in file_names]

    years = [dt.year for dt in dts]
    months = [dt.month for dt in dts]
    days = [dt.day for dt in dts]

    return years, months, days


def _get_history_files(component_name, stream_name, start_year, end_year,
                       calendar, history_streams):
    """
    Get a list of available history files from the given stream
    """

    start_date = f'{start_year:04d}-01-01_00:00:00'
    if end_year is None:
        end_date = None
    else:
        end_date = f'{end_year:04d}-12-31_23:59:59'

    input_files = history_streams.readpath(
        stream_name, start_date=start_date, end_date=end_date,
        calendar=calendar)

    if len(input_files) == 0:
        raise ValueError(f'No input files found for stream {stream_name} in '
                         f'{component_name} between {start_year} and '
                         f'{end_year}')

    input_files = sorted(input_files)

    return input_files


def _update_time_bounds_from_file_names(config, time_bounds_section, years,
                                        months):
    """
    Update the start and end years and dates for time series, climatologies or
    climate indices based on the years actually available in the list of files.
    """

    error_on_missing = config.getboolean('input', 'errorOnMissing')

    requested_start_year, requested_end_year = \
        _get_start_and_end_year(config, time_bounds_section)

    # search for the start of the first full year
    first_index = 0
    while first_index < len(years) and months[first_index] != 1:
        first_index += 1
    start_year = years[first_index]

    # search for the end of the last full year
    last_index = len(years) - 1
    while last_index >= 0 and months[last_index] != 12:
        last_index -= 1
    end_year = years[last_index]

    if requested_end_year is None:
        config.set(time_bounds_section, 'endYear', str(end_year))
        requested_end_year = end_year

    if start_year != requested_start_year or end_year != requested_end_year:
        if error_on_missing:
            raise ValueError(
                f"{time_bounds_section} start and/or end year different from "
                f"requested\n"
                f"requested: {requested_start_year:04d}-"
                f"{requested_end_year:04d}\n"
                f"actual:   {start_year:04d}-{end_year:04d}\n")
        else:
            print(
                f"Warning: {time_bounds_section} start and/or end year "
                f"different from requested\n"
                f"requested: {requested_start_year:04d}-"
                f"{requested_end_year:04d}\n"
                f"actual:   {start_year:04d}-{end_year:04d}\n")
            config.set(time_bounds_section, 'startYear', str(start_year))
            config.set(time_bounds_section, 'endYear', str(end_year))

    start_date = f'{start_year:04d}-01-01_00:00:00'
    config.set(time_bounds_section, 'startDate', start_date)
    end_date = f'{start_year:04d}-12-31_23:59:59'
    config.set(time_bounds_section, 'endDate', end_date)


def _create_symlinks(config, input_files, years, months, days, component_name,
                     stream_name):
    """
    Create local symlinks for the files from this stream in the input
    subdirectory of the output path
    """

    # for file prefix, remove the redundant "Output" ending (if any) from the
    # stream name
    stream_prefix = stream_name.replace('Output', '')

    input_subdirectory = build_config_full_path(config, 'output',
                                                'inputSubdirectory')
    symlink_directory = f'{input_subdirectory}/{component_name}'

    make_directories(symlink_directory)

    for in_file_name, year, month, day in \
            zip(input_files, years, months, days):
        out_file_name = f'{symlink_directory}/' \
                        f'{stream_prefix}.{year:04d}-{month:02d}-{day:02d}.nc'

        try:
            os.symlink(in_file_name, out_file_name)
        except OSError:
            pass

    return symlink_directory
