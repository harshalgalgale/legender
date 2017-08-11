# -*- coding: utf-8 -*-
import requests
from PIL.PngImagePlugin import PngImageFile

from nose import tools

from legender import GeoServer, Legend

GS_URL = 'https://gsavalik.envir.ee/geoserver'

GS_WORKSPACE = 'keskkonnainfo'
GS_LYRNAME = 'keskkonnainfo:ristipuud'
GS_LYRGEOMNAME = 'shape'
GS_LYRBBOX_POINT = [661431,6399178,661631,6399378]
GS_LYRBBOX_POLYGON = [647490,6387380,647690,6387580]
GS_LYRSRS = 'EPSG:3301'

GS_LEGEND_CONF = {}

GS_WORKSPACE_NO_WFS = 'baasandmed'
GS_LYRNAME_NO_WFS = 'baasandmed:black'

def test_split_layername():
    gs = GeoServer(GS_URL)
    inputs = 'black:magic'
    expect = ('black', 'magic')
    print 'Test split layername'
    tools.assert_equals(gs.split_layername(inputs), expect)

def test_split_layername_no_workspace():
    gs = GeoServer(GS_URL)
    inputs = 'abracadabra'
    expect = (None, 'abracadabra')
    print 'Test split layername with no workspace'
    tools.assert_equals(gs.split_layername(inputs), expect)

def test_service_url():
    gs = GeoServer(GS_URL)
    inputs = 'rumpelstiltskin'
    expect = '%s/rumpelstiltskin/ows' % GS_URL
    print 'Test service url with workspace'
    tools.assert_equals(gs.service_url(inputs), expect)

def test_service_url_no_workspace():
    gs = GeoServer(GS_URL)
    inputs = None
    expect = '%s/ows' % GS_URL
    print 'Test service url with NO workspace'
    tools.assert_equals(gs.service_url(inputs), expect)

###
# WFS preflight checks
###

def test_wfs_get_feature_preflight():
    gs = GeoServer(GS_URL)
    inputs = (GS_WORKSPACE, GS_LYRNAME)
    print 'Test preflight wfs'
    data = gs.do_preflight_wfs(*inputs)
    tools.assert_in('wfs_available', data)
    tools.assert_in('features_present', data)
    tools.assert_in('geometry_name', data)

@tools.raises(requests.HTTPError)
def test_wfs_get_feature_preflight_no_layer():
    gs = GeoServer(GS_URL)
    inputs = ('black', 'black:magic')
    print 'Test preflight wfs with false layername'
    data = gs.do_preflight_wfs(*inputs)

def test_wfs_get_feature_preflight_no_wfs():
    gs = GeoServer(GS_URL)
    inputs = (GS_WORKSPACE_NO_WFS, GS_LYRNAME_NO_WFS)
    print 'Test preflight wfs with no wfs enabled'
    data = gs.do_preflight_wfs(*inputs)
    tools.assert_in('wfs_available', data)
    tools.assert_false(data['wfs_available'])

###
# Building CQL_FILTER for geometrytype
###

def test_cql_filter_construct_geometrytype_point():
    gs = GeoServer(GS_URL)
    inputs = ('Point', 'shape')
    expect = "((geometryType(shape)='Point')OR(geometryType(shape)='MultiPoint'))"
    print 'Test CQL geometrytype filter construct for point (check spelling!)'
    tools.assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

def test_cql_filter_construct_geometrytype_linestring():
    gs = GeoServer(GS_URL)
    inputs = ('LineString', 'shape')
    expect = "((geometryType(shape)='LineString')OR(geometryType(shape)='MultiLineString'))"
    print 'Test CQL geometrytype filter construct for linestring (check spelling!)'
    tools.assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

def test_cql_filter_construct_geometrytype_polygon():
    gs = GeoServer(GS_URL)
    inputs = ('Polygon', 'shape')
    expect = "((geometryType(shape)='Polygon')OR(geometryType(shape)='MultiPolygon'))"
    print 'Test CQL geometrytype filter construct for polygon (check spelling!)'
    tools.assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

def test_cql_filter_construct_geometrytype_polygon_passing_multi_is_ok():
    gs = GeoServer(GS_URL)
    inputs = ('MultiPolygon', 'shape')
    expect = "((geometryType(shape)='Polygon')OR(geometryType(shape)='MultiPolygon'))"
    print 'Test CQL geometrytype filter construct for MultiPolygon (check spelling!)'
    tools.assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

@tools.raises(AssertionError)
def test_cql_filter_construct_geometrytype_polygon_wrong_spelling():
    gs = GeoServer(GS_URL)
    inputs = ('polygon', 'shape')
    print 'Test CQL geometrytype filter construct for "polygon" not "Polygon"'
    gs.construct_cql_for_geometrytype(*inputs)

@tools.raises(AssertionError)
def test_cql_filter_construct_geometrytype_unknown_type():
    gs = GeoServer(GS_URL)
    inputs = ('LinearRing', 'shape')
    print 'Test CQL geometrytype filter construct for unknown type ("LinearRing")'
    gs.construct_cql_for_geometrytype(*inputs)

def test_sql_filter_add_additional():
    gs = GeoServer(GS_URL)
    inputs = ('Point', 'shape')
    cql_filter = gs.construct_cql_for_geometrytype(*inputs)
    additional_inputs = (cql_filter, 'the_meaning=42')
    expect = "(((geometryType(shape)='Point')OR(geometryType(shape)='MultiPoint'))AND(the_meaning=42))"
    print 'Test CQL geometrytype filter construct and add aditional'
    tools.assert_equals(
        gs.add_additional_filter(*additional_inputs),
        expect
    )

###
# WFS GetFeature
###

def test_get_feature_point():
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'Point')
    print 'Test GetFeature on %s for sample Point/MultiPoint' % GS_LYRNAME
    feature = gs.get_feature(*inputs)
    if feature != None:
        tools.assert_is_instance(feature, dict)
        tools.assert_in('id', feature)
        tools.assert_in('geometry', feature)
        tools.assert_in(feature['geometry']['type'], ['Point', 'MultiPoint'])

def test_get_feature_linestring():
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'LineString')
    print 'Test GetFeature on %s for sample LineString/MultiLineString' % GS_LYRNAME
    feature = gs.get_feature(*inputs)
    if feature != None:
        tools.assert_is_instance(feature, dict)
        tools.assert_in('id', feature)
        tools.assert_in('geometry', feature)
        tools.assert_in(feature['geometry']['type'], ['LineString', 'MultiLineString'])

def test_get_feature_polygon():
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'Polygon')
    print 'Test GetFeature on %s for sample Polygon/MultiPolygon' % GS_LYRNAME
    feature = gs.get_feature(*inputs)
    if feature != None:
        tools.assert_is_instance(feature, dict)
        tools.assert_in('id', feature)
        tools.assert_in('geometry', feature)
        tools.assert_in(feature['geometry']['type'], ['Polygon', 'MultiPolygon'])

###
# WMS GetMap
###

def test_get_map_gs_point():
    out_filename = 'test_img/get_map_gs_point.png'
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'Point', GS_LYRGEOMNAME,
        GS_LYRBBOX_POINT, GS_LYRSRS)
    img = gs.get_map(*inputs)
    print 'Test GetMap with previously checked location (point feature)'
    tools.assert_is_instance(img, PngImageFile)
    tools.assert_is_not_none(img.getbbox())
    img.save(out_filename, 'PNG')

def test_get_map_gs_polygon():
    out_filename = 'test_img/get_map_gs_polygon.png'
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'Polygon', GS_LYRGEOMNAME,
        GS_LYRBBOX_POLYGON, GS_LYRSRS)
    img = gs.get_map(*inputs)
    print 'Test GetMap with previously checked location (polygon feature)'
    tools.assert_is_instance(img, PngImageFile)
    tools.assert_is_not_none(img.getbbox())
    img.save(out_filename, 'PNG')

def test_get_map_gs_linestring():
    out_filename = 'test_img/get_map_gs_linestring.png'
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'LineString', GS_LYRGEOMNAME,
        GS_LYRBBOX_POLYGON, GS_LYRSRS)
    img = gs.get_map(*inputs)
    print 'Test GetMap with previously checked location (linestring feature)'
    tools.assert_is_instance(img, PngImageFile)
    img.save(out_filename, 'PNG')

###
# Building a legend
###

def test_legend_properties_full():
    legend_conf = {
        "title":"wat?",
        "styles":["a", "list", "of", "stylenames"],
        "filter": "an_arbitrary_sql_filter(expression)",
        "bbox": [1,2,3,4],
        "srs": "EPSG:-1"}
    print 'Test Legend instance properties all'
    l = Legend(GeoServer, GS_URL, 'black:magic', legend_conf)
    tools.assert_true(hasattr(l, 'server'))
    tools.assert_is_instance(l.server, GeoServer)
    tools.assert_equals(l.server.url, GS_URL)

    tools.assert_true(hasattr(l, 'title'))
    tools.assert_equals(l.title, legend_conf['title'])

    tools.assert_true(hasattr(l, 'styles'))
    tools.assert_is_instance(l.styles, list)
    tools.assert_equals(l.styles, legend_conf['styles'])

    tools.assert_true(hasattr(l, 'filter'))
    tools.assert_equals(l.filter, legend_conf['filter'])

    tools.assert_true(hasattr(l, 'bbox'))
    tools.assert_true(isinstance(l.bbox, list))

    tools.assert_true(hasattr(l, 'srs'))
    tools.assert_equals(l.srs, legend_conf['srs'])

def test_legend_properties_minimal():
    legend_conf = {}
    print 'Test Legend instance properties minimal'
    l = Legend(GeoServer, GS_URL, 'black:magic', legend_conf)
    tools.assert_true(hasattr(l, 'server'))
    tools.assert_is_instance(l.server, GeoServer)
    tools.assert_equals(l.server.url, GS_URL)

    tools.assert_true(hasattr(l, 'title'))
    tools.assert_equals(l.title, 'black:magic')

    tools.assert_true(hasattr(l, 'styles'))
    tools.assert_is_instance(l.styles, list)
    tools.assert_equals(l.styles, ['default'])

    tools.assert_true(hasattr(l, 'filter'))
    tools.assert_is_none(l.filter)

    tools.assert_true(hasattr(l, 'bbox'))
    tools.assert_is_none(l.bbox)

    tools.assert_true(hasattr(l, 'srs'))
    tools.assert_is_none(l.srs)

def test_legend_thumbnail_create_minimal():
    legend_conf = {
        "srs":"EPSG:3301"
    }
    print 'Test legend thumbnail creation with minimal config'
    l = Legend(GeoServer, GS_URL, GS_LYRNAME, legend_conf)
    l.create_thumbnails('./test_img')
