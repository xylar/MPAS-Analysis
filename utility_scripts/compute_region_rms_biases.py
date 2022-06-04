#!/usr/bin/env python

import xarray
import numpy


def main():

    mask_filename = \
        'Antarctic_Regions_6000.0x6000.0km_10.0km_Antarctic_stereo.nc'

    ds_masks = xarray.open_dataset(mask_filename)
    region_names = list(ds_masks.regionNames.values)
    masks = ds_masks.regionMasks

    in_filenames = {
        'Standard Resolution': {
            'mpas': '/lcrc/group/acme/ac.dcomeau/scratch/chrys/mpas_analysis_output/20220429.CRYO1850.ne30pg2_ECwISC30to60E2r1.chrysalis.CryoBranchHorTaperGMVisbeckRediconst/yrs71-100/clim/mpas/avg/remapped/schmidtko_ECwISC30to60E2r1_to_6000.0x6000.0km_10.0km_Antarctic_stereo/mpaso_ANN_007101_010012_climo.nc',
            'obs_temp': '/lcrc/group/acme/ac.dcomeau/scratch/chrys/mpas_analysis_output/20220429.CRYO1850.ne30pg2_ECwISC30to60E2r1.chrysalis.CryoBranchHorTaperGMVisbeckRediconst/yrs71-100/clim/obs/temperatureSchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc',
            'obs_salin': '/lcrc/group/acme/ac.dcomeau/scratch/chrys/mpas_analysis_output/20220429.CRYO1850.ne30pg2_ECwISC30to60E2r1.chrysalis.CryoBranchHorTaperGMVisbeckRediconst/yrs71-100/clim/obs/salinitySchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc'},
        'SORRM': {
            'mpas': '/lcrc/group/acme/ac.dcomeau/scratch/chrys/mpas_analysis_output/20220426.CRYO1850.ne30pg2_SOwISC12to60E2r4.chrysalis.CryoBranchHorTaperGMVisbeckRediconst/yrs71-100/clim/mpas/avg/remapped/schmidtko_SOwISC12to60E2r4_to_6000.0x6000.0km_10.0km_Antarctic_stereo/mpaso_ANN_007101_010012_climo.nc',
            'obs_temp': '/lcrc/group/acme/ac.dcomeau/scratch/chrys/mpas_analysis_output/20220426.CRYO1850.ne30pg2_SOwISC12to60E2r4.chrysalis.CryoBranchHorTaperGMVisbeckRediconst/yrs71-100/clim/obs/temperatureSchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc',
            'obs_salin': '/lcrc/group/acme/ac.dcomeau/scratch/chrys/mpas_analysis_output/20220426.CRYO1850.ne30pg2_SOwISC12to60E2r4.chrysalis.CryoBranchHorTaperGMVisbeckRediconst/yrs71-100/clim/obs/salinitySchmidtko_6000.0x6000.0km_10.0km_Antarctic_stereo_ANN.nc'}}

    biases = dict()

    for mesh_name, filenames in in_filenames.items():
        biases[mesh_name] = dict()
        for field, obs_file, mpas_field, obs_field in [
               ('Temperature', 'obs_temp', 'timeMonthly_avg_activeTracers_temperature', 'botTheta'),
               ('Salinity', 'obs_salin', 'timeMonthly_avg_activeTracers_salinity', 'botSalinity')]:

            biases[mesh_name][field] = dict()

            ds_mpas = xarray.open_dataset(filenames['mpas']).isel(depthSlice=0)
            ds_obs = xarray.open_dataset(filenames[obs_file]).isel(depthSlice=0)
            # obs have x and y transposed relative to mpas and the masks
            ds_obs = ds_obs.rename({'y': 'x', 'x': 'y'})
            bias = (ds_mpas[mpas_field] - ds_obs[obs_field])
            valid_mask = bias.notnull()
            bias = bias.where(valid_mask, other=0.)

            for region in range(masks.sizes['nRegions']):
                region_name = region_names[region]
                mask = valid_mask*masks.isel(nRegions=region)
                variance = (mask*bias**2).mean()/mask.mean()
                rms_bias = numpy.sqrt(variance).values
                biases[mesh_name][field][region_name] = rms_bias
                ds_local = xarray.Dataset()
                ds_local.coords['lon'] = ds_obs['lon']
                ds_local.coords['lat'] = ds_obs['lat']
                ds_local['lon_mpas'] = ds_mpas['lon']
                ds_local['lat_mpas'] = ds_mpas['lat']
                ds_local['bias'] = mask*bias
                ds_local['valid_mask'] = valid_mask
                ds_local['region_mask'] = masks.isel(nRegions=region)
                ds_local['mask'] = mask
                filename = f'bias_{mesh_name}_{field}_{region_name}.nc'
                filename = filename.replace(' ', '_')
                ds_local.to_netcdf(filename)


    for field in ['Temperature', 'Salinity']:
        print_string = [field] + list(biases)
        print(', '.join(print_string))
        for region_name in region_names:
            if 'Deep' in region_name or '60S' in region_name:
                continue
            print_string = [region_name]
            for mesh_name in biases:
                print_string.append(
                    f'{biases[mesh_name][field][region_name]:.2f}')
            print(', '.join(print_string))


if __name__ == '__main__':
    main()
