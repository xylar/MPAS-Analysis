#!/usr/bin/env python

import xarray as xr
import numpy as np
from mpas_tools.io import write_netcdf


in_filename = '/lcrc/group/e3sm/ac.mhoffman/acme_scratch/anvil/20191003.GMPAS-IAF-ISMF.T62_oEC60to30v3wLI.cori-knl/run/mpaso.rst.0102-01-01_00000.nc'
out_filename = '/lcrc/group/e3sm/ac.xylar/analysis/hoffman_et_al_2023/fake_restart/mpaso.rst.0102-01-01_00000.nc'
test_filename = '/lcrc/group/e3sm/ac.xylar/analysis/hoffman_et_al_2023/fake_restart/fixMaxLevelCell.nc'
ds = xr.open_dataset(in_filename)

max_level_cell = ds.maxLevelCell
coc = ds.cellsOnCell - 1
nEdgesOnCell = ds.nEdgesOnCell
nCells = ds.sizes['nCells']
maxEdges = ds.sizes['maxEdges']

ds_out = xr.Dataset()
deepest_neighbor = np.zeros(nCells, dtype=int)
for i in range(maxEdges):
    mask = np.logical_and(i < nEdgesOnCell, coc[:, i] >= 0)
    neighbor = coc[mask, i]
    deepest_neighbor[mask] = np.maximum(deepest_neighbor[mask],
                                        max_level_cell[neighbor])
    ds_out[f'deepestNeighbor{i}'] = ('nCells', deepest_neighbor.copy())

ds_out['deepestNeighbor'] = ('nCells', deepest_neighbor)
deepest_neighbor = ds_out.deepestNeighbor
mask = max_level_cell <= deepest_neighbor
ds_out['mask'] = mask.astype(float)
new_max_level_cell = xr.where(mask, max_level_cell, deepest_neighbor)

ds_out['newMaxLevelCell'] = new_max_level_cell
ds['maxLevelCell'] = new_max_level_cell

write_netcdf(ds, out_filename)
write_netcdf(ds_out, test_filename)
