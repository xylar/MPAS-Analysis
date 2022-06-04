#!/usr/bin/env python
import numpy
import xarray
from inpoly import inpoly2

from geometric_features import GeometricFeatures, FeatureCollection
from geometric_features.aggregation import get_aggregator_by_name


def main():
    directory = \
        '/lcrc/group/acme/ac.dcomeau/scratch/chrys/mpas_analysis_output/' \
        '20220426.CRYO1850.ne30pg2_SOwISC12to60E2r4.chrysalis.CryoBranchHorTaperGMVisbeckRediconst/' \
        'yrs71-100/clim/mpas/avg/remapped/' \
        'schmidtko_SOwISC12to60E2r4_to_6000.0x6000.0km_10.0km_Antarctic_stereo'
    grid_filename = f'{directory}/mpaso_ANN_007101_010012_climo.nc'
    print(grid_filename)

    ds_in = xarray.open_dataset(grid_filename)
    lon = ds_in.lon.values
    lat = ds_in.lat.values

    agg_function, prefix, date = \
        get_aggregator_by_name(region_group='Antarctic Regions')

    gf = GeometricFeatures()
    fc = agg_function(gf)

    masks = numpy.zeros((len(fc.features), lon.shape[0], lon.shape[1]))
    region_names = []
    for index, feature in enumerate(fc.features):
        fc_local = FeatureCollection()
        fc_local.add_feature(feature)
        masks[index, :, :] = mask_from_feature_collection(fc_local, lon, lat)
        region_names.append(feature['properties']['name'])

    out_filename = \
        'Antarctic_Regions_6000.0x6000.0km_10.0km_Antarctic_stereo.nc'
    ds_out = xarray.Dataset()
    for coord in ['lon', 'lat']:
        ds_out.coords[coord] = ds_in[coord]
    for coord in ['lon_bnds', 'lat_bnds']:
        ds_out[coord] = ds_in[coord]

    ds_out['regionMasks'] = (('nRegions', 'y', 'x'), masks)
    ds_out['regionNames'] = (('nRegions',), region_names)

    ds_out.to_netcdf(out_filename)


def mask_from_feature_collection(fc, lon, lat):

    nodes = list()
    edges = list()
    for feature in fc.features:
        if feature['geometry']['type'] == 'Polygon':
            for poly in feature['geometry']['coordinates']:
                _add_poly(poly, edges, nodes)

        elif feature['geometry']['type'] == 'MultiPolygon':
            for mpoly in feature['geometry']['coordinates']:
                for poly in mpoly:
                    _add_poly(poly, edges, nodes)

    nodes = numpy.array(nodes)
    edges = numpy.array(edges)

    points = numpy.vstack([lon.ravel(), lat.ravel()]).T

    in_shape, _ = inpoly2(points, nodes, edges)

    mask = in_shape.reshape(lon.shape)
    return mask


def _add_poly(poly, edges, nodes):
    node_count = len(nodes)
    edge_count = len(poly)
    poly_edges = [[node_count + edge,
                   node_count + (edge + 1) % edge_count] for edge in
                  range(edge_count)]
    edges.extend(poly_edges)
    nodes.extend(poly)


if __name__ == '__main__':
    main()


