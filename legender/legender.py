# -*- coding: utf-8 -*-
import requests

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
        preflight_check = self.do_preflight_wfs(workspace, layername)

    def do_preflight_wfs(self, workspace, layername):
        """Do some pre-flight WFS checks

        a. is WFS supported?
        b. does the layer contain any features?
        c. what's the geom property name?
        """
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
        url = self.service_url(workspace)
        params = dict(
            service='WFS',
            request='GetFeature',
            version='2.0.0',
            outputFormat='application/json',
        )
        kwargs.update(params)
        return self._do_query('json', url, **kwargs)

    def _do_query(self, returns, url, **kwargs):
        r = self.session.get(
            url,
            params=kwargs
        )
        r.raise_for_status()
        fn = getattr(r, returns)
        try:
            response = fn()
        except Exception as e:
            request = r.url
            raise ValueError(
                'Tried to get %s from %s, instead got gibberish.' % (
                    returns, request
                ))
        return response
