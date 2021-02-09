#!/usr/bin/env python
# This software is open source software available under the BSD-3 license.
#
# Copyright (c) 2020 Triad National Security, LLC. All rights reserved.
# Copyright (c) 2020 Lawrence Livermore National Security, LLC. All rights
# reserved.
# Copyright (c) 2020 UT-Battelle, LLC. All rights reserved.
#
# Additional copyright and license information can be found in the LICENSE file
# distributed with this code, or at
# https://raw.githubusercontent.com/MPAS-Dev/MPAS-Analysis/master/LICENSE

"""
Creates a region mask file from ISMIP6 regions on the ISMIP6 8km polar
stereographic grid.  Both a geojson file for the regions and the mask file
will be stored in the given output directory.  Because mask computation with
shapely is relatively slow, the computation can be sped up by running several
threads in parallel.

Usage: Symlink the mpas_analysis directory from one directory up.
Modify the mesh and regions names and the local path to region masks and mesh
file. Optionally, change the number of threads.
"""

import xarray
import logging
import sys
import os

from geometric_features import GeometricFeatures
from geometric_features.aggregation.ocean import ismip6

from mpas_analysis.shared.regions.compute_region_masks_subtask import \
    compute_projection_grid_region_masks


meshName = 'ISMIP6_8km'

regionsName = 'ismip6Regions20210201'

# the number of parallel threads to use
processCount = 8

regionMasksPath = '/home/xylar/Desktop/region_masks'

# replace with the path to the desired mesh or restart file
meshFileName = '/home/xylar/Desktop/obs_temperature_1995-2017_8km_x_60m.nc'

try:
    os.makedirs(regionMasksPath)
except OSError:
    pass

geojsonFileName = '{}/{}.geojson'.format(regionMasksPath, regionsName)
maskFileName = '{}/{}_{}.nc'.format(regionMasksPath, meshName, regionsName)

logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

if not os.path.exists(geojsonFileName):
    gf = GeometricFeatures()
    fc = ismip6(gf)
    fc.to_geojson(geojsonFileName)

with xarray.open_dataset(meshFileName) as ds:
    lon = ds.lon
    lat = ds.lat
    compute_projection_grid_region_masks(geojsonFileName, lon, lat,
                                         maskFileName, logger=logger,
                                         processCount=processCount)
