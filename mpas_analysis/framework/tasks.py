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


from mpas_analysis import ocean
from mpas_analysis import sea_ice
from mpas_analysis.shared.climatology import MpasClimatologyTask, \
    RefYearMpasClimatologyTask
from mpas_analysis.shared.time_series import MpasTimeSeriesTask

from mpas_analysis.shared.regions import ComputeRegionMasks


def build_analysis_list(config, control_config):
    """
    Build a list of analysis tasks. New tasks should be added here, following
    the approach used for existing analysis tasks.

    Parameters
    ----------
    config : mpas_tools.config.MpasConfigParser
        contains config options

    control_config : mpas_tools.config.MpasConfigParser or None
        contains config options for a control run, or ``None`` if no config
        file for a control run was specified

    Returns
    -------
    analyses : list
        A list of all analysis tasks
    """

    analyses = []

    # Ocean Analyses
    ocean_climatology_tasks = {}
    for op in ['avg', 'min', 'max']:
        ocean_climatology_tasks[op] = MpasClimatologyTask(
            config=config, componentName='ocean', op=op)
    ocean_time_series_task = MpasTimeSeriesTask(
        config=config, componentName='ocean')
    ocean_index_task = MpasTimeSeriesTask(
        config=config, componentName='ocean', section='index')

    ocean_ref_year_climatology_task = RefYearMpasClimatologyTask(
        config=config, componentName='ocean')

    ocean_region_masks_task = ComputeRegionMasks(
        config=config, conponentName='ocean')

    for op in ocean_climatology_tasks:
        analyses.append(ocean_climatology_tasks[op])
    analyses.append(ocean_ref_year_climatology_task)

    analyses.append(ocean.ClimatologyMapMLD(
        config, ocean_climatology_tasks['avg'], control_config))

    analyses.append(ocean.ClimatologyMapMLDMinMax(
        config, ocean_climatology_tasks, control_config))

    analyses.append(ocean.ClimatologyMapSST(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.ClimatologyMapSSS(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.ClimatologyMapSSH(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.ClimatologyMapEKE(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.ClimatologyMapOHCAnomaly(
        config, ocean_climatology_tasks['avg'],
        ocean_ref_year_climatology_task, control_config))

    analyses.append(ocean.ClimatologyMapSose(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.ClimatologyMapWoa(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.ClimatologyMapBGC(
        config, ocean_climatology_tasks['avg'], control_config))

    analyses.append(ocean.ClimatologyMapArgoTemperature(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.ClimatologyMapArgoSalinity(
        config, ocean_climatology_tasks['avg'], control_config))

    analyses.append(ocean.ClimatologyMapSchmidtko(
        config, ocean_climatology_tasks['avg'], control_config))

    analyses.append(ocean.ClimatologyMapAntarcticMelt(
        config, ocean_climatology_tasks['avg'], ocean_region_masks_task,
        control_config))

    analyses.append(ocean.RegionalTSDiagrams(
        config, ocean_climatology_tasks['avg'], ocean_region_masks_task,
        control_config))

    analyses.append(ocean.TimeSeriesAntarcticMelt(
        config, ocean_time_series_task, ocean_region_masks_task,
        control_config))

    analyses.append(ocean.TimeSeriesOceanRegions(
        config, ocean_region_masks_task, control_config))

    analyses.append(ocean.TimeSeriesTemperatureAnomaly(
        config, ocean_time_series_task))
    analyses.append(ocean.TimeSeriesSalinityAnomaly(
        config, ocean_time_series_task))
    analyses.append(ocean.TimeSeriesOHCAnomaly(
        config, ocean_time_series_task, control_config))
    analyses.append(ocean.TimeSeriesSSHAnomaly(
        config, ocean_time_series_task, control_config))
    analyses.append(ocean.TimeSeriesSST(
        config, ocean_time_series_task, control_config))
    analyses.append(ocean.TimeSeriesTransport(config, control_config))

    analyses.append(ocean.MeridionalHeatTransport(
        config, ocean_climatology_tasks['avg'], control_config))

    analyses.append(ocean.StreamfunctionMOC(
        config, ocean_climatology_tasks['avg'], control_config))
    analyses.append(ocean.IndexNino34(
        config, ocean_index_task, control_config))

    analyses.append(ocean.WoceTransects(
        config, ocean_climatology_tasks['avg'], control_config))

    analyses.append(ocean.SoseTransects(
        config, ocean_climatology_tasks['avg'], control_config))

    analyses.append(ocean.GeojsonTransects(
        config, ocean_climatology_tasks['avg'], control_config))

    ocean_regional_profile = ocean.OceanRegionalProfiles(
        config, ocean_region_masks_task, control_config)
    analyses.append(ocean_regional_profile)

    analyses.append(ocean.HovmollerOceanRegions(
        config, ocean_region_masks_task, ocean_regional_profile,
        control_config))

    # Sea Ice Analyses
    sea_ice_climatology_task = MpasClimatologyTask(
        config=config, componentName='seaIce')
    sea_ice_time_series_task = MpasTimeSeriesTask(
        config=config, componentName='seaIce')

    analyses.append(sea_ice_climatology_task)
    analyses.append(sea_ice.ClimatologyMapSeaIceConc(
        config=config, mpasClimatologyTask=sea_ice_climatology_task,
        hemisphere='NH', controlConfig=control_config))
    analyses.append(sea_ice.ClimatologyMapSeaIceThick(
        config=config, mpasClimatologyTask=sea_ice_climatology_task,
        hemisphere='NH', controlConfig=control_config))
    analyses.append(sea_ice.ClimatologyMapSeaIceConc(
        config=config, mpasClimatologyTask=sea_ice_climatology_task,
        hemisphere='SH', controlConfig=control_config))
    analyses.append(sea_ice.ClimatologyMapSeaIceThick(
        config=config, mpasClimatologyTask=sea_ice_climatology_task,
        hemisphere='SH', controlConfig=control_config))
    analyses.append(sea_ice_time_series_task)

    analyses.append(sea_ice.TimeSeriesSeaIce(config, sea_ice_time_series_task,
                                             control_config))

    # Iceberg Analyses
    analyses.append(sea_ice.ClimatologyMapIcebergConc(
        config=config, mpasClimatologyTask=sea_ice_climatology_task,
        hemisphere='SH', controlConfig=control_config))

    return analyses
