#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017,  Los Alamos National Security, LLC (LANS)
# and the University Corporation for Atmospheric Research (UCAR).
#
# Unless noted otherwise source code is licensed under the BSD license.
# Additional copyright and license information can be found in the LICENSE file
# distributed with this code, or at http://mpas-dev.github.com/license.html
#
"""
Define skill scores for comparison of two datasets, e.g., model vs observations.

Skill scores are adapted from the following references:

    Overview and cross-skill score comparisions:
    Ralston, D. K., Geyer, W. R., & Lerczak, J. A. (2010). Structure, variability,
    and salt flux in a strongly forced salt wedge estuary. Journal of Geophysical
    Research: Oceans, 115(C6).
    doi:10.1029/2009JC005806
    https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2009JC005806

    Murphy Skill Score SS:
    Murphy, A. H. (1988), Skill scores based on the mean square error and their
    relationships to the correlation coefficient, Mon. Weather Rev., 116(12),
    2417–2424, doi:10.1175/1520-0493(1988)116<2417: SSBOTM>2.0.CO;2.
    https://journals.ametsoc.org/doi/abs/10.1175/1520-0493(1988)116%3C2417:SSBOTM%3E2.0.CO%3B2

    Pearson correlation coefficient r:
    Crow, E. L., Davis, F. A., Maxfield, M. W., & Maxfield, M. W. (1960).
    Statistics manual: with examples taken from ordnance development (Vol.
    3369). Courier Corporation.
    https://en.wikipedia.org/wiki/Pearson_correlation_coefficient

    Coefficient of determination r^2:
    Crow, E. L., Davis, F. A., Maxfield, M. W., & Maxfield, M. W. (1960).
    Statistics manual: with examples taken from ordnance development (Vol.
    3369). Courier Corporation.
    https://en.wikipedia.org/wiki/Coefficient_of_determination

    Wilmott skill score SSw:
    Wilmott, C. (1981), On the validation of models, Phys. Geogr., 2, 184–194.
    http://onlinelibrary.wiley.com/doi/10.1029/2004JC002691/epdf
"""
# Authors
# -------
# Phillip J. Wolfram

from __future__ import absolute_import, division, print_function, \
    unicode_literals

import numpy as np


def murphy_ss(Xmod, Xobs): #{{{
    """
    Murphy skill score from
    Murphy, A. H. (1988), Skill scores based on the mean square error and their
    relationships to the correlation coefficient, Mon. Weather Rev., 116(12),
    2417–2424, doi:10.1175/1520-0493(1988)116<2417: SSBOTM>2.0.CO;2.
    https://journals.ametsoc.org/doi/abs/10.1175/1520-0493(1988)116%3C2417:SSBOTM%3E2.0.CO%3B2

     max SS=1 for perfect agreement,
            0 is equal agreement as mean,
            negative less predictive than mean of observations

     Allen et al., 2007's assessment provides qualitative descriptor
     from their hydrodynamic-ecosystem model:

         > 0.65 as excellent
         0.5 to 0.65 very good
         0.2 to 0.5 as good
         < 0.2 as poor

    From Ralston et al (2010), comparing across scores:
    "if we compare two sets of randomly generated numbers between 0 and 1 (105
    elements), we find that r ≈ 0.0 (no correlation), SS ≈ −1.0 (no
    predictive skill), and SSw ≈ 0.4."
    """
    # Authors
    # -------
    # Phillip J. Wolfram

    # rmserror between model and observations
    rmserror = np.nansum((Xmod - Xobs)**2.0)

    # observation standard deviation
    obsstd = np.nansum((Xobs - np.nanmean(Xobs))**2.0)

    # skill score
    SS = 1.0 - rmserror/obsstd

    return SS #}}}


def correlation_coeff_r(Xmod, Xobs): #{{{
    """
    Standard statistical Pearson correlation coefficient r.

    Crow, E. L., Davis, F. A., Maxfield, M. W., & Maxfield, M. W. (1960).
    Statistics manual: with examples taken from ordnance development (Vol.
    3369). Courier Corporation.
    https://en.wikipedia.org/wiki/Pearson_correlation_coefficient

    r measures the linear relationship between the model and observations where
    1 is total positive linear correlation (perfect agreement), 0 is no linear
    correlation (uncorrelated), and −1 is total negative linear correlation
    (anti-correlated).

    From Ralston et al (2010), comparing across scores:
    "if we compare two sets of randomly generated numbers between 0 and 1 (105
    elements), we find that r ≈ 0.0 (no correlation), SS ≈ −1.0 (no
    predictive skill), and SSw ≈ 0.4."
    """
    # Authors
    # -------
    # Phillip J. Wolfram

    # standard stats
    crosscorr = np.nansum((Xmod - np.nanmean(Xmod))*(Xobs - np.nanmean(Xobs)))
    modcorr = np.nansum((Xmod - np.nanmean(Xmod))**2.0)
    obscorr = np.nansum((Xobs - np.nanmean(Xobs))**2.0)

    r = crosscorr / np.sqrt(modcorr*obscorr)

    return r #}}}


def coeff_determination_r2(Xmod, Xobs): #{{{
    """
    Standard statistical coefficient of determination r^2.

    r^2 is a commonly used measure to designate "goodness of fit" where perfect
    agreement is 1.  This is one of the most commonly used statistical measures
    and it is the square of the Pearson correlation coefficient.

    Crow, E. L., Davis, F. A., Maxfield, M. W., & Maxfield, M. W. (1960).
    Statistics manual: with examples taken from ordnance development (Vol.
    3369). Courier Corporation.
    https://en.wikipedia.org/wiki/Coefficient_of_determination
    """

    return correlation_coeff_r(Xmod, Xobs)**2.0 #}}}


def wilmott_ssw(Xmod, Xobs): #{{{
    """
    The Wilmott skill score from
    Wilmott, C. (1981), On the validation of models, Phys. Geogr., 2, 184–194.
    http://onlinelibrary.wiley.com/doi/10.1029/2004JC002691/epdf

    From Ralston et al (2010):
    "if we compare two sets of randomly generated numbers between 0 and 1 (105
    elements), we find that r ≈ 0.0 (no correlation), SS ≈ −1.0 (no
    predictive skill), and SSw ≈ 0.4."

    """
    # Authors
    # -------
    # Phillip J. Wolfram

    meanbias = np.nansum((Xmod - Xobs)**2.0)
    relbias = np.nansum((np.abs(Xmod - np.nanmean(Xmod)) + np.abs(Xobs - np.nanmean(Xobs)))**2.0)

    SSw = 1.0 - meanbias/relbias

    return SSw #}}}

skillscores = {'Murphy skill score SS': murphy_ss,
               'Pearson Correlation Coefficient r': correlation_coeff_r,
               'Coefficient of determination r^2': coeff_determination_r2,
               'Wilmott skill score SSw': wilmott_ssw}

# vim: foldmethod=marker ai ts=4 sts=4 et sw=4 ft=python
