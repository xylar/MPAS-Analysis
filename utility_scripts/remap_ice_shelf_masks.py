#!/usr/bin/env python

import xarray

from mpas_analysis.shared.interpolation import Remapper
from mpas_analysis.shared.grid import MpasMeshDescriptor
from mpas_analysis.shared.climatology import get_comparison_descriptor
from mpas_analysis.configuration import MpasAnalysisConfigParser


# replace with the MPAS mesh name
inGridName = 'oRRS30to10v3wLI'

# replace with the path to the desired mesh or restart file
inGridFileName = '/project/projectdirs/acme/inputdata/ocn/mpas-o/oRRS30to10v3wLI/oRRS30to10v3wLI.171109.nc'

config = MpasAnalysisConfigParser()
config.read('mpas_analysis/config.default')
# replace 1.0 with the desired resolution of the output mesh

inDescriptor = MpasMeshDescriptor(inGridFileName, inGridName)

outDescriptor = get_comparison_descriptor(config, 'antarctic')
outGridName = outDescriptor.meshName

mappingFileName = '/global/homes/x/xylar/acme/mpas_analysis/mapping/map_{}_to_{}_bilinear.nc'.format(inGridName, outGridName)

remapper = Remapper(inDescriptor, outDescriptor, mappingFileName)

remapper.build_mapping_file(method='bilinear')

dsIn = xarray.open_dataset('/global/homes/x/xylar/acme/mpas_analysis/region_masks/oRRS30to10v3wLI_iceShelfMasks.nc')

dsIn=dsIn.isel(nRegions=[1, 10, 19, 22])

print(dsIn.regionNames)

ds = xarray.Dataset()
for name in ['regionCellMasks', 'regionNames']:
    ds[name] = dsIn[name]

ds = remapper.remap(ds)
ds.to_netcdf('iceShelfMasks_{}.nc'.format(outGridName))



