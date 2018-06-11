#!/usr/bin/env python

import xarray

outGridName = '6000.0x6000.0km_10.0km_Antarctic_stereo'
masks = xarray.open_dataset('iceShelfMasks_{}.nc'.format(outGridName))
regionNames = [bytes.decode(name) for name in masks.regionNames.values]

inFileNames = [{'grid': 'oEC60to30v3wLI',
                'mpas': '/global/cscratch1/sd/mpeterse/analysis/20180511.GMPAS-IAF.T62_oEC60to30v3wLI.edison/yrs11-30/clim/mpas/remapped/schmidtko_oEC60to30v3wLI_to_6000.0x6000.0km_10.0km_Antarctic_stereo/mpaso_ANN_001101_003012_climo.nc', 
                'obsTemp': '/global/cscratch1/sd/mpeterse/analysis/20180511.GMPAS-IAF.T62_oEC60to30v3wLI.edison/yrs11-30/clim/obs/temperatureSchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc',
                'obsSalin': '/global/cscratch1/sd/mpeterse/analysis/20180511.GMPAS-IAF.T62_oEC60to30v3wLI.edison/yrs11-30/clim/obs/salinitySchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc'},
               {'grid': 'oRRS30to10v3wLI',
                'mpas': '/global/cscratch1/sd/mpeterse/analysis/20180209.GMPAS-IAF.T62_oRRS30to10v3wLI.cori-knl.afterSalinityFix.yrs11-30/clim/mpas/remapped/schmidtko_oRRS30to10v3wLI_to_6000.0x6000.0km_10.0km_Antarctic_stereo/mpaso_ANN_001101_003012_climo.nc',
                'obsTemp': '/global/cscratch1/sd/mpeterse/analysis/20180209.GMPAS-IAF.T62_oRRS30to10v3wLI.cori-knl.afterSalinityFix.yrs11-30/clim/obs/temperatureSchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc',
                'obsSalin': '/global/cscratch1/sd/mpeterse/analysis/20180209.GMPAS-IAF.T62_oRRS30to10v3wLI.cori-knl.afterSalinityFix.yrs11-30/clim/obs/salinitySchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc'}]

for inFileName in inFileNames:
    print('{}: Temperature'.format(inFileName['grid']))
    dsMpas = xarray.open_dataset(inFileName['mpas']).isel(depthSlice=0)
    dsObs = xarray.open_dataset(inFileName['obsTemp']).isel(depthSlice=0)
    bias = dsMpas.timeMonthly_avg_activeTracers_temperature - dsObs.botTheta
    rmsBias = xarray.ufuncs.sqrt((bias**2).mean()).values
    print('Antarctica: {}'.format(rmsBias))

    for region in range(masks.sizes['nRegions']):
        regionName = regionNames[region]
        mask = masks.regionCellMasks.isel(nRegions=region).where(bias.notnull())
        variance = (mask*bias**2).mean()/mask.mean()
        rmsBias = xarray.ufuncs.sqrt(variance).values
        print('{}: {}'.format(regionName, rmsBias))

    print('{}: Salinity'.format(inFileName['grid']))
    dsMpas = xarray.open_dataset(inFileName['mpas']).isel(depthSlice=0)
    dsObs = xarray.open_dataset(inFileName['obsSalin']).isel(depthSlice=0)
    bias = dsMpas.timeMonthly_avg_activeTracers_salinity - dsObs.botSalinity
    rmsBias = xarray.ufuncs.sqrt((bias**2).mean()).values
    print('Antarctica: {}'.format(rmsBias))

    for region in range(masks.sizes['nRegions']):
        regionName = regionNames[region]
        mask = masks.regionCellMasks.isel(nRegions=region).where(bias.notnull())
        variance = (mask*bias**2).mean()/mask.mean()
        rmsBias = xarray.ufuncs.sqrt(variance).values
        print('{}: {}'.format(regionName, rmsBias))
