# -*- coding: utf-8 -*-
import requests

from nose.tools import assert_equals, assert_in
from nose.tools import raises
from legender import GeoServer

GS_URL = 'https://gsavalik.envir.ee/geoserver'
GS_WORKSPACE = 'keskkonnainfo'
GS_LYRNAME = 'keskkonnainfo:ristipuud'

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
