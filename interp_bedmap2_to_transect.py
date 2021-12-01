#!/usr/bin/env python
import xarray
import pyproj


proj = pyproj.Proj('epsg:3031')

ds_bed = xarray.open_dataset('bedmap2.nc')

ds = xarray.Dataset()
ds['bed'] = ds_bed.bed
ds['draft'] = ds_bed.surface - ds_bed.thickness
ds['ice_mask'] = ds_bed.icemask_shelves + ds_bed.icemask_grounded


for transect_name in ['Filchner', 'Ronne']:
    path = f'/lcrc/group/e3sm/ac.xylar/comeau_et_al_revisions/vgm_transect/' \
           f'yrs171-200/clim/mpas/avg/remapped/' \
           f'geojson_ECwISC30to60E1r2_to_{transect_name}'

    ds_trans = xarray.open_dataset(f'{path}/mpas_transect_info.nc')
    x, y = proj(ds_trans.lonNode, ds_trans.latNode)

    ds_index = xarray.Dataset()
    ds_index['x'] = (('nSegments', 'nHorizBounds'), x)
    ds_index['y'] = (('nSegments', 'nHorizBounds'), y)


    ds_out = ds.interp(x=ds_index.x, y=ds_index.y)
    ds_out['dNode'] = ds_trans.dNode

    ds_out.to_netcdf(f'{transect_name}_bedmap2_transect.nc')



