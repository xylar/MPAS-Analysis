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
import gsw
import numpy as np
import xarray as xr

from mpas_analysis.ocean.compute_transects_subtask import \
    ComputeTransectsSubtask


class ComputeTransectsWithSigma(ComputeTransectsSubtask):
    """
    Add neutral density from potential temperature and practical salinity
    """
    # Authors
    # -------
    # Xylar Asay-Davis

    def customize_masked_climatology(self, climatology, season):
        """
        Construct velocity magnitude as part of the climatology

        Parameters
        ----------
        climatology : ``xarray.Dataset`` object
            the climatology data set

        season : str
            The name of the season to be masked

        Returns
        -------
        climatology : ``xarray.Dataset`` object
            the modified climatology data set
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # first, call the base class's version of this function so we extract
        # the desired slices.
        climatology = super().customize_masked_climatology(climatology,
                                                           season)

        lonmean = -40.
        latmean = 26.5

        # Read in depth and bin latitudes
        try:
            restartFileName = self.runStreams.readpath('restart')[0]
        except ValueError:
            raise IOError('No MPAS-O restart file found: need at least '
                          'one for MHT calcuation')

        with xr.open_dataset(restartFileName) as dsRestart:
            refBottomDepth = dsRestart.refBottomDepth.values

        nVertLevels = len(refBottomDepth)
        refLayerThickness = np.zeros(nVertLevels)
        refLayerThickness[0] = refBottomDepth[0]
        refLayerThickness[1:nVertLevels] = \
            refBottomDepth[1:nVertLevels] - refBottomDepth[0:nVertLevels - 1]

        z = -(refBottomDepth - 0.5 * refLayerThickness)

        if 'timeMonthly_avg_activeTracers_temperature' in climatology and \
                'timeMonthly_avg_activeTracers_salinity' in climatology:
            
            pt = climatology.timeMonthly_avg_activeTracers_temperature
            sp = climatology.timeMonthly_avg_activeTracers_salinity
            pressure = xr.DataArray(dims=('nVertLevels',),
                                    data=gsw.p_from_z(z, latmean))
            sa = gsw.SA_from_SP(sp, pressure, lonmean, latmean)
            ct = gsw.CT_from_pt(sa, pt)
            sigma2 = gsw.density.sigma2(sa, ct)
            sigma0 = gsw.density.sigma0(sa, ct)

            climatology['sigma2'] = sigma2
            climatology.sigma2.attrs['units'] = 'kg m$^{-3}$'
            climatology.sigma2.attrs['description'] = \
                'potential density anomaly (ref 2000 dbar)'

            climatology['sigma0'] = sigma0
            climatology.sigma0.attrs['units'] = 'kg m$^{-3}$'
            climatology.sigma0.attrs['description'] = \
                'potential density anomaly'

        return climatology
