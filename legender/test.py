# -*- coding: utf-8 -*-
import requests
from PIL.PngImagePlugin import PngImageFile

from nose.tools import (assert_equals, assert_in, assert_false,
    assert_is_instance, assert_is_not_none, assert_not_equal)
from nose.tools import raises

from legender import GeoServer

GS_URL = 'https://gsavalik.envir.ee/geoserver'

GS_WORKSPACE = 'keskkonnainfo'
GS_LYRNAME = 'keskkonnainfo:ristipuud'
GS_LYRGEOMNAME = 'shape'
GS_LYRBBOX_POINT = [661431,6399178,661631,6399378]
GS_LYRBBOX_POLYGON = [647490,6387380,647690,6387580]
GS_LYRSRS = 'EPSG:3301'

GS_WORKSPACE_NO_WFS = 'baasandmed'
GS_LYRNAME_NO_WFS = 'baasandmed:black'

def test_split_layername():
    gs = GeoServer(GS_URL)
    inputs = 'black:magic'
    expect = ('black', 'magic')
    print 'Test split layername'
    assert_equals(gs.split_layername(inputs), expect)

def test_split_layername_no_workspace():
    gs = GeoServer(GS_URL)
    inputs = 'abracadabra'
    expect = (None, 'abracadabra')
    print 'Test split layername with no workspace'
    assert_equals(gs.split_layername(inputs), expect)

def test_service_url():
    gs = GeoServer(GS_URL)
    inputs = 'rumpelstiltskin'
    expect = '%s/rumpelstiltskin/ows' % GS_URL
    print 'Test service url with workspace'
    assert_equals(gs.service_url(inputs), expect)

def test_service_url_no_workspace():
    gs = GeoServer(GS_URL)
    inputs = None
    expect = '%s/ows' % GS_URL
    print 'Test service url with NO workspace'
    assert_equals(gs.service_url(inputs), expect)

###
# WFS preflight checks
###

def test_wfs_get_feature_preflight():
    gs = GeoServer(GS_URL)
    inputs = (GS_WORKSPACE, GS_LYRNAME)
    print 'Test preflight wfs'
    data = gs.do_preflight_wfs(*inputs)
    assert_in('wfs_available', data)
    assert_in('features_present', data)
    assert_in('geometry_name', data)

@raises(requests.HTTPError)
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
    assert_in('wfs_available', data)
    assert_false(data['wfs_available'])

###
# Building CQL_FILTER for geometrytype
###

def test_cql_filter_construct_geometrytype_point():
    gs = GeoServer(GS_URL)
    inputs = ('Point', 'shape')
    expect = "((geometryType(shape)='Point')OR(geometryType(shape)='MultiPoint'))"
    print 'Test CQL geometrytype filter construct for point (check spelling!)'
    assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

def test_cql_filter_construct_geometrytype_linestring():
    gs = GeoServer(GS_URL)
    inputs = ('LineString', 'shape')
    expect = "((geometryType(shape)='LineString')OR(geometryType(shape)='MultiLineString'))"
    print 'Test CQL geometrytype filter construct for linestring (check spelling!)'
    assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

def test_cql_filter_construct_geometrytype_polygon():
    gs = GeoServer(GS_URL)
    inputs = ('Polygon', 'shape')
    expect = "((geometryType(shape)='Polygon')OR(geometryType(shape)='MultiPolygon'))"
    print 'Test CQL geometrytype filter construct for polygon (check spelling!)'
    assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

def test_cql_filter_construct_geometrytype_polygon_passing_multi_is_ok():
    gs = GeoServer(GS_URL)
    inputs = ('MultiPolygon', 'shape')
    expect = "((geometryType(shape)='Polygon')OR(geometryType(shape)='MultiPolygon'))"
    print 'Test CQL geometrytype filter construct for MultiPolygon (check spelling!)'
    assert_equals(
        gs.construct_cql_for_geometrytype(*inputs),
        expect
    )

@raises(AssertionError)
def test_cql_filter_construct_geometrytype_polygon_wrong_spelling():
    gs = GeoServer(GS_URL)
    inputs = ('polygon', 'shape')
    print 'Test CQL geometrytype filter construct for "polygon" not "Polygon"'
    gs.construct_cql_for_geometrytype(*inputs)

@raises(AssertionError)
def test_cql_filter_construct_geometrytype_unknown_type():
    gs = GeoServer(GS_URL)
    inputs = ('LinearRing', 'shape')
    print 'Test CQL geometrytype filter construct for unknown type ("LinearRing")'
    gs.construct_cql_for_geometrytype(*inputs)

###
# WFS GetFeature
###

def test_get_feature_point():
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'Point')
    print 'Test GetFeature on %s for sample Point/MultiPoint' % GS_LYRNAME
    feature = gs.get_feature(*inputs)
    if feature != None:
        assert_is_instance(feature, dict)
        assert_in('id', feature)
        assert_in('geometry', feature)
        assert_in(feature['geometry']['type'], ['Point', 'MultiPoint'])

def test_get_feature_linestring():
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'LineString')
    print 'Test GetFeature on %s for sample LineString/MultiLineString' % GS_LYRNAME
    feature = gs.get_feature(*inputs)
    if feature != None:
        assert_is_instance(feature, dict)
        assert_in('id', feature)
        assert_in('geometry', feature)
        assert_in(feature['geometry']['type'], ['LineString', 'MultiLineString'])

def test_get_feature_polygon():
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'Polygon')
    print 'Test GetFeature on %s for sample Polygon/MultiPolygon' % GS_LYRNAME
    feature = gs.get_feature(*inputs)
    if feature != None:
        assert_is_instance(feature, dict)
        assert_in('id', feature)
        assert_in('geometry', feature)
        assert_in(feature['geometry']['type'], ['Polygon', 'MultiPolygon'])

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
    assert_is_instance(img, PngImageFile)
    assert_is_not_none(img.getbbox())
    img.save(out_filename, 'PNG')

def test_get_map_gs_polygon():
    out_filename = 'test_img/get_map_gs_polygon.png'
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'Polygon', GS_LYRGEOMNAME,
        GS_LYRBBOX_POLYGON, GS_LYRSRS)
    img = gs.get_map(*inputs)
    print 'Test GetMap with previously checked location (polygon feature)'
    assert_is_instance(img, PngImageFile)
    assert_is_not_none(img.getbbox())
    img.save(out_filename, 'PNG')

def test_get_map_gs_linestring():
    out_filename = 'test_img/get_map_gs_linestring.png'
    gs = GeoServer(GS_URL)
    inputs = (GS_LYRNAME, 'LineString', GS_LYRGEOMNAME,
        GS_LYRBBOX_POLYGON, GS_LYRSRS)
    img = gs.get_map(*inputs)
    print 'Test GetMap with previously checked location (linestring feature)'
    assert_is_instance(img, PngImageFile)
    img.save(out_filename, 'PNG')
