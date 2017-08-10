# -*- coding: utf-8 -*-
import requests

from PIL import Image
from StringIO import StringIO

class GeoServer(object):
    def __init__(self, url, **kwargs):
        self.session = requests.Session()
        if "username" in kwargs:
            _user = kwargs.pop("username")
            _pass = kwargs.pop("password")
            self.session.auth = (_user, _pass)
        self.url = url.rstrip('/')

    def get_feature(self, layername, geometrytype):
        """Query for a sample feature of from WFS endpoint"""
        workspace, _ = self.split_layername(layername)
        geometry_name = self.do_preflight_checks(workspace, layername)
        params = dict(
            typename=layername,
            count=1,
            cql_filter=self.construct_cql_for_geometrytype(
                geometrytype,geometry_name)
        )
        fc = self._do_wfs_get_feature(workspace, **params)
        features = fc['features']
        if len(features) == 0:
            return None
        feature = features[0]
        return feature

    def get_map(self, layername, geometrytype, geometryname, bbox, srs,
        transparent=True, additional_filter=None, featureid=None,
        style='default', size=(100, 100)):
        """Query WMS endpoint for a piece of map layer to be used for legend."""
        workspace, _ = self.split_layername(layername)
        if featureid != None:
            cql_filter = None
        else:
            cql_filter = self.construct_cql_for_geometrytype(
                geometrytype, geometryname)
            # @TODO apply additional_filter
        width, height = size
        params = dict(
            layers=layername,
            bbox=','.join(['%s' % coord for coord in bbox]),
            srs=srs,
            transparent=transparent,
            cql_filter=cql_filter,
            featureid=featureid,
            style=style,
            width=width,
            height=height
        )
        data = self._do_wms_get_map(workspace, **params)
        img = Image.open(StringIO(data))
        return img

    def construct_cql_for_geometrytype(self, geometrytype, geometry_name):
        """Constructs a geometry type CQL filter for use in GetFeature/GetMap
        requests.
        """
        known = ['Point', 'Polygon', 'LineString']
        gt = geometrytype.lstrip('Multi')
        assert gt in known, "'%s' is not a known geometrytype: [%s]" % (
            gt, ','.join(known)
        )
        cql = "((geometryType(%s)='%s')OR(geometryType(%s)='Multi%s'))" % (
            geometry_name, gt, geometry_name, gt
        )
        return cql

    def do_preflight_checks(self, workspace, layername):
        """Do WFS preflight checks

        a. is WFS supported?
        b. does the layer contain any features?
        c. what's the geom property name?
        """
        preflight_check = self.do_preflight_wfs(workspace, layername)
        assert preflight_check['wfs_available'] == True, "WFS endpoint not available"
        if preflight_check['features_present'] == False:
            raise IOError(
                'No features present @ %s' % layername
            )
        return preflight_check['geometry_name']

    def do_preflight_wfs(self, workspace, layername):
        """Request data for pre-flight WFS checks"""
        params = dict(
            typename=layername,
            count=1
        )
        checks = {}
        # if no WFS then this will fail with ValueError
        try:
            fc = self._do_wfs_get_feature(workspace, **params)
            checks['wfs_available'] = True
        except ValueError as ve:
            checks['wfs_available'] = False
        else:
            features = fc['features']
            if len(features) == 0:
                checks['features_present'] = False
                checks['geometry_name'] = None
            else:
                checks['features_present'] = True
                checks['geometry_name'] = features[0]['geometry_name']
        return checks

    def split_layername(self, layername):
        """Splits GeoServer's workspace-qualified layername into ws name and
        layername.
        """
        parts = layername.split(':')
        if len(parts) == 2:
            workspace, layername = parts
        else:
            workspace = None
            layername = parts[0]
        return workspace, layername

    def service_url(self, workspace):
        """Returns GeoServer's workspace URL to ows endpoint."""
        url = '/'.join(
            [bit for bit in [
                self.url,
                workspace,
                'ows'
            ] if bit != None]
        )
        return url

    def _do_wfs_get_feature(self, workspace, **kwargs):
        """Prepare and submit a GetFeature HTTP Get query."""
        url = self.service_url(workspace)
        params = dict(
            service='WFS',
            request='GetFeature',
            version='2.0.0',
            outputFormat='application/json',
        )
        kwargs.update(params)
        return self._do_query('json', url, **kwargs)

    def _do_wms_get_map(self, workspace, **kwargs):
        """Prepare and submit a GetMap HTTP Get query."""
        url = self.service_url(workspace)
        params = dict(
            service='WMS',
            request='GetMap',
            version='1.1.0',
            format='image/png'
        )
        kwargs.update(params)
        return self._do_query('content', url, **kwargs)

    def _do_query(self, returns, url, **kwargs):
        """Do a HTTP GET query, return response.

        @param returns: defines the requests.Response method to call
            on the returned data (e.g. C{json}, C{xml}, C{text}, etc).
        @type returns: C{str}
        """
        r = self.session.get(
            url,
            params=kwargs
        )
        r.raise_for_status()
        fn = getattr(r, returns)
        try:
            if callable(fn):
                return fn()
            return fn
        except Exception as e:
            raise ValueError(
                'Tried to get requests.%s from %s, instead got gibberish.' % (
                    returns, r.url
                ))
        return response
