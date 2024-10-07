# -*- coding: utf-8 -*-
# This software is open source software available under the BSD-3 license.
#
# Copyright (c) 2022 Triad National Security, LLC. All rights reserved.
# Copyright (c) 2022 Lawrence Livermore National Security, LLC. All rights
# reserved.
# Copyright (c) 2022 UT-Battelle, LLC. All rights reserved.
#
# Additional copyright and license information can be found in the LICENSE file
# distributed with this code, or at
# https://raw.githubusercontent.com/MPAS-Dev/MPAS-Analysis/main/LICENSE
#

import os
import xarray

from mpas_analysis.shared import AnalysisTask
from mpas_analysis.ocean.plot_hovmoller_subtask import PlotHovmollerSubtask

from mpas_analysis.shared.io import write_netcdf_with_fill

from mpas_analysis.shared.timekeeping.utility import \
    get_simulation_start_time, string_to_datetime

from mpas_analysis.shared.timekeeping.MpasRelativeDelta import \
    MpasRelativeDelta

from mpas_analysis.shared.io.utility import build_config_full_path

from mpas_analysis.shared.time_series import \
    compute_moving_avg_anomaly_from_start


class HovmollerOceanRegions(AnalysisTask):
    """
    Compute and plot a Hovmoller diagram (depth vs. time) for regionally
    analyzed data.  The mean of the data are computed over each region at each
    depth and time.
    """
    # Authors
    # -------
    # Xylar Asay-Davis

    def __init__(self, config, regionMasksTask, oceanRegionalProfilesTask,
                 controlConfig=None):
        """
        Construct the analysis task.

        Parameters
        ----------
        config :  mpas_tools.config.MpasConfigParser
            Contains configuration options

        regionMasksTask : ``ComputeRegionMasks``
            A task for computing region masks

        oceanRegionalProfilesTask : mpas_analysis.ocean.OceanRegionalProfiles
            A task for computing ocean regional profiles

        controlconfig : mpas_tools.config.MpasConfigParser, optional
            Configuration options for a control run (if any)
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call the constructor from the base class (AnalysisTask)
        super(HovmollerOceanRegions, self).__init__(
            config=config,
            taskName='hovmollerOceanRegions',
            componentName='ocean',
            tags=['profiles', 'timeSeries', 'hovmoller'])

        startYear = config.getint('timeSeries', 'startYear')
        endYear = config.getint('timeSeries', 'endYear')

        regionGroups = config.getexpression('hovmollerOceanRegions',
                                            'regionGroups')

        allowedFields = config.getexpression('oceanRegionalProfiles',
                                             'allowedFields')

        for regionGroup in regionGroups:
            suffix = regionGroup[0].upper() + regionGroup[1:].replace(' ', '')
            regionGroupSection = f'hovmoller{suffix}'
            regionNames = config.getexpression(regionGroupSection,
                                               'regionNames')
            if len(regionNames) == 0:
                return

            fields, anyAnomalies = _get_fields(
                config, regionGroupSection, allowedFields)

            masksSubtask = regionMasksTask.add_mask_subtask(regionGroup)
            masksFile = masksSubtask.geojsonFileName
            timeSeriesName = regionGroup.replace(' ', '')

            regionNames = masksSubtask.expand_region_names(regionNames)

            self.masksSubtask = masksSubtask

            oceanRegionalProfilesTask.add_region_group(
                regionMasksTask, regionGroup, regionNames,
                fields, startYear, endYear)

            combineSubtask = oceanRegionalProfilesTask.combineSubtasks[
                regionGroup][(startYear, endYear)]

            movingAveragePoints = config.getint(
                regionGroupSection, 'movingAveragePoints')

            baseDirectory = build_config_full_path(
                config, 'output', 'timeSeriesSubdirectory')

            # PlotHovmollerSubtask requires a relative path
            combinedFileName = \
                f'{timeSeriesName}/regionalProfiles_{timeSeriesName}_' \
                f'{startYear:04d}-{endYear:04d}.nc'
            if anyAnomalies:
                inFullPath = f'{baseDirectory}/{combinedFileName}'
                anomalyFileName = \
                    f'{timeSeriesName}/anomaly_{timeSeriesName}_' \
                    f'{startYear:04d}-{endYear:04d}.nc'
                outFullPath = f'{baseDirectory}/{anomalyFileName}'
                anomalySubtask = ComputeHovmollerAnomalySubtask(
                    self, inFullPath, outFullPath, movingAveragePoints)
                self.add_subtask(anomalySubtask)
                anomalySubtask.run_after(combineSubtask)
            else:
                anomalySubtask = None
                anomalyFileName = None

            for field in fields:
                prefix = field['prefix']
                plotAnomaly = field['anomaly']
                suffix = prefix[0].upper() + prefix[1:]
                fieldSectionName = f'hovmollerOceanRegions{suffix}'

                config.set(fieldSectionName, 'movingAveragePoints',
                           f'{movingAveragePoints}')

                for regionName in regionNames:
                    regionNameClean = regionName.replace('_', ' ')
                    if plotAnomaly:
                        titleName = f'{field["titleName"]} Anomaly'
                        caption = f'Anomaly of {regionNameClean} ' \
                                  f'{titleName} vs depth'
                        galleryGroup = f'{regionGroup} Anomaly vs Depths'
                        subtaskName = f'plotHovmollerAnomaly_{prefix}_' \
                                      f'{regionNameClean}'
                        inFileName = anomalyFileName
                    else:
                        titleName = field['titleName']
                        anomalySubtask = None
                        caption = f'Time series of {regionNameClean} ' \
                                  f'{titleName} vs depth'
                        galleryGroup = \
                            f'{regionGroup} Time Series vs Depths'
                        subtaskName = \
                            f'plotHovmoller_{prefix}_{regionNameClean}'
                        inFileName = combinedFileName

                    groupLink = f'ocnreghovs_' \
                                f'{regionGroup.replace(" ", "").lower()}'
                    hovmollerSubtask = PlotHovmollerSubtask(
                        parentTask=self,
                        regionName=regionName,
                        inFileName=inFileName,
                        outFileLabel=f'{prefix}_hovmoller',
                        fieldNameInTitle=titleName,
                        mpasFieldName=f'{prefix}_mean',
                        unitsLabel=field['units'],
                        sectionName=fieldSectionName,
                        thumbnailSuffix='',
                        imageCaption=caption,
                        galleryGroup=galleryGroup,
                        groupSubtitle=None,
                        groupLink=groupLink,
                        galleryName=titleName,
                        subtaskName=subtaskName,
                        controlConfig=controlConfig,
                        regionMaskFile=masksFile)
                    if plotAnomaly:
                        hovmollerSubtask.run_after(anomalySubtask)
                    else:
                        hovmollerSubtask.run_after(combineSubtask)
                    self.add_subtask(hovmollerSubtask)

        self.run_after(oceanRegionalProfilesTask)


class ComputeHovmollerAnomalySubtask(AnalysisTask):
    """
    A subtask for computing anomalies of moving averages and writing them out.

    Attributes
    ----------
    inFileName : str
        The file name for the time series

    outFileName : str
        The file name (usually without full path) where the resulting
        data set should be written

    movingAveragePoints : int
        The number of points (months) used in the moving average used to
        smooth the data set
    """
    # Authors
    # -------
    # Xylar Asay-Davis

    def __init__(self, parentTask, inFileName, outFileName,
                 movingAveragePoints, subtaskName='computeAnomaly'):
        """
        Construct the analysis task.

        Parameters
        ----------
        parentTask : ``AnalysisTask``
            The parent task of which this is a subtask

        inFileName : str
            The file name for the time series

        outFileName : str
            The file name for the anomaly

        movingAveragePoints : int
            The number of months used in the moving average used to
            smooth the data set

        subtaskName :  str, optional
            The name of the subtask
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call the constructor from the base class (AnalysisTask)
        super(ComputeHovmollerAnomalySubtask, self).__init__(
            config=parentTask.config,
            taskName=parentTask.taskName,
            componentName='ocean',
            tags=parentTask.tags,
            subtaskName=subtaskName)

        self.inFileName = inFileName
        self.outFileName = outFileName
        self.movingAveragePoints = movingAveragePoints

    def setup_and_check(self):
        """
        Perform steps to set up the analysis and check for errors in the setup.
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call setup_and_check from the base class (AnalysisTask),
        # which will perform some common setup, including storing:
        #     self.runDirectory , self.historyDirectory, self.plotsDirectory,
        #     self.namelist, self.runStreams, self.historyStreams,
        #     self.calendar
        super(ComputeHovmollerAnomalySubtask, self).setup_and_check()

        startDate = self.config.get('timeSeries', 'startDate')
        endDate = self.config.get('timeSeries', 'endDate')

        delta = MpasRelativeDelta(string_to_datetime(endDate),
                                  string_to_datetime(startDate),
                                  calendar=self.calendar)

        months = delta.months + 12*delta.years

        if months <= self.movingAveragePoints:
            raise ValueError('Cannot meaningfully perform a rolling mean '
                             'because the time series is too short.')

    def run_task(self):
        """
        Performs analysis of ocean heat content (OHC) from time-series output.
        """
        # Authors
        # -------
        # Xylar Asay-Davis, Milena Veneziani, Greg Streletz

        self.logger.info("\nComputing anomalies...")

        config = self.config

        ds = xarray.open_dataset(self.inFileName)

        dsStart = ds.isel(Time=slice(0, self.movingAveragePoints)).mean('Time')

        for variable in ds.data_vars:
            ds[variable] = ds[variable] - dsStart[variable]

        outFileName = self.outFileName
        if not os.path.isabs(outFileName):
            baseDirectory = build_config_full_path(
                config, 'output', 'timeSeriesSubdirectory')

            outFileName = '{}/{}'.format(baseDirectory,
                                         outFileName)

        write_netcdf_with_fill(ds, outFileName)


def _get_fields(config, regionGroupSection, allowedFields):
    """
    Get a list of fields, adding an entry in each indicating whether anomalies
    should be computed/plotted
    """
    fields = []

    noAnomalyList = config.getexpression(regionGroupSection, 'fields')
    anomalyList = config.getexpression(regionGroupSection, 'anomalyFields')

    anyAnomalies = len(anomalyList) > 0

    for field in allowedFields:
        fieldName = field['prefix']
        if fieldName in noAnomalyList:
            local = field.copy()
            local['anomaly'] = False
            fields.append[local]
            noAnomalyList.pop(fieldName)
        if fieldName in anomalyList:
            local = field.copy()
            local['anomaly'] = True
            fields.append[local]
            anomalyList.pop(fieldName)

    if noAnomalyList:
        raise ValueError(
            f'{list(noAnomalyList)} not found in '
            f'oceanRegionalProfiles/allowedFields')

    if anomalyList:
        raise ValueError(
            f'{list(anomalyList)} not found in '
            f'oceanRegionalProfiles/allowedFields')

    return fields, anyAnomalies
