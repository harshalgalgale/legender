# -*- coding: utf-8 -*-
import os, requests

from PIL import Image, ImageDraw, ImageOps
from StringIO import StringIO
from shapely.geometry import asShape, Point

class GeoServer(object):
    def __init__(self, url, **kwargs):
        self.session = requests.Session()
        if "username" in kwargs:
            _user = kwargs.pop("username")
            _pass = kwargs.pop("password")
            self.session.auth = (_user, _pass)
        self.url = url.rstrip('/')

    def get_feature(self, layername, geometrytype, additional_filter=None):
        """Query for a sample feature of from WFS endpoint"""
        workspace, _ = self.split_layername(layername)
        geometry_name = self.do_preflight_checks(workspace, layername)
        cql_filter = self.construct_cql_for_geometrytype(
            geometrytype,geometry_name)
        cql_filter = self.add_additional_filter(cql_filter, additional_filter)
        params = dict(
            typename=layername,
            count=1,
            cql_filter=cql_filter
        )
        fc = self._do_wfs_get_feature(workspace, **params)
        features = fc['features']
        if len(features) == 0:
            return None
        feature = features[0]
        return feature

    def get_map(self, layername, geometrytype, geometryname, bbox, srs,
        transparent=True, additional_filter=None, featureid=None,
        style='default', size=(100, 100), geometrytype_filtering=True):
        """Query WMS endpoint for a piece of map layer to be used for legend."""
        workspace, _ = self.split_layername(layername)
        if featureid != None:
            cql_filter = None
        else:
            cql_filter = self.construct_cql_for_geometrytype(
                geometrytype, geometryname, geometrytype_filtering)
            cql_filter = self.add_additional_filter(cql_filter, additional_filter)
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

    def add_additional_filter(self, cql_filter, additional_filter):
        if additional_filter == None:
            return cql_filter
        args = [cql_filter, additional_filter]
        # just stack geometry_type filtering and additional with AND for now
        cql_filter = '(%s)' % ')AND('.join([a for a in args if a != None])
        return cql_filter

    def construct_cql_for_geometrytype(self, geometrytype, geometry_name,
            compose_filter=True):
        """Constructs a geometry type CQL filter for use in GetFeature/GetMap
        requests.

        If compose_filter == C{False} or geometry_name == C{None} no filter
        expression is created.
        """
        if geometry_name == None or compose_filter != True:
            return
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


class Legend(object):
    _gutter = 10
    def __init__(self, cls, url, layername, conf={}):
        self.server = cls(url)
        self.layername = layername
        self.title = conf.get('title', layername)
        self.styles = conf.get('styles', ['default'])
        self.filter = conf.get('filter', None)
        self.bbox = conf.get('bbox', None)
        self.srs = conf.get('srs', None)
        # NB! srs needs to be set in any case!
        # unless we dive into WMS Capabilities, brrrrr....

    def create_thumbnails(self, path):
        """Get and merge thumbnails for this configuration.

        Do styling things here aswell (e.g. add titles and whatnot)
        """
        for stylename in self.styles:
            filename = '%s__%s.png' % (
                ''.join([s for s in self.layername if s not in ':.,']),
                ''.join([s for s in stylename if s not in ':.,'])
            )
            thumbs = []
            for geometrytype in ['Point', 'LineString', 'Polygon']:
                try:
                    thumb = self._create_thumbnail(
                        stylename, geometrytype, self.filter
                    )
                except AssertionError as ae:
                    pass
                else:
                    if not self.is_empty_image(thumb):
                        thumb = self.apply_mask(thumb)
                        thumbs.append(thumb)
            img = self.merge_thumbnails(thumbs)
            if img != None:
                img.save(os.path.join(path, filename), "PNG")

    def apply_mask(self, thumb):
        """Make thumbnail round (that's all hip now, ain't it?), add outline."""
        width, height = thumb.size
        # antialias
        bigsize = (width * 4, height * 4)
        linewidth = 12
        mask = Image.new('RGBA', bigsize, (255, 255, 255, 255))
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + bigsize, fill=(27, 29, 28, 255))
        draw.ellipse(
            (linewidth, linewidth) + (bigsize[0] - linewidth, bigsize[1] - linewidth),
            fill=(255, 255, 255, 0))
        mask = mask.resize(thumb.size, Image.ANTIALIAS)
        thumb.paste(mask, (0, 0), mask)
        return thumb

    def is_empty_image(self, img):
        """Check if the returned image is completely black/white."""
        extr = img.convert("L").getextrema()
        if extr in [(0, 0), (255, 255)]:
            return True
        return False

    def merge_thumbnails(self, thumbs=[]):
        """Merge getmap thumbnails into one image."""
        n = len(thumbs)
        if n == 0:
            return
        gutter = self._gutter
        width, height = ((100 * n) + gutter * n + gutter, 100 + gutter * 2)
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        for i, thumb in enumerate(thumbs):
            location = ((i * 100) + gutter + (i * gutter), gutter)
            img.paste(thumb, location)
        return img

    def _create_thumbnail(self, stylename, geometrytype, filter):
        """Get image data and make a thumbnail for a layer for this style and
        geometry_type.
        """
        if self.bbox == None:
            # will try to get bbox from WFS
            feature = self.server.get_feature(
                self.layername, geometrytype, self.filter)
            assert feature != None, "No WFS %s features returned for layer '%s' using cql_filter '%s'" % (
                geometrytype, self.layername, self.filter
            )
            bbox = self.get_bbox_from_feature(feature)
            geometry_name = feature.get('geometry_name')
        else:
            bbox = self.bbox
        if self.srs == None:
            raise AttributeError(
                "SRS (e.g 'EPSG:4326') not supplied in init conf, or undetermined from WFS request."
            )
        return self.server.get_map(self.layername, geometrytype, geometry_name,
            bbox, self.srs,
            transparent=False, additional_filter=None, featureid=None,
            style=stylename, size=(100, 100))

    def get_bbox_from_feature(self, feature, buffer_size=100):
        """Some shapely magic.

        NB! geometry coordinates expected to be in meters! This (i.e
        buffer_size) should be  either configurable, or deductible from
        layer crs.
        """
        assert "geometry" in feature, "This feature has no 'geometry' member"
        geometry = feature["geometry"]
        geometry_type = feature["geometry"]["type"]
        shape = asShape(geometry)
        if geometry_type == 'Point':
            # center bbox over geometry
            pnt = shape
        elif geometry_type == 'LineString':
            # center bbox over 1/2 distance of line
            pnt = shape.interpolate(0.5, normalized=True)
        elif geometry_type == 'Polygon':
            # center bbox over whatever vertice?
            # Nope. get boundary and fall back to linestring :P
            b = shape.boundary
            return self.get_bbox_from_feature(
                {"geometry": b.__geo_interface__, "type":"Feature"},
                buffer_size)
        elif geometry_type.startswith('Multi'):
            # HA-HA-HA :D
            # what the ???
            geom = shape.geoms[0]
            return self.get_bbox_from_feature(
                {"geometry": geom.__geo_interface__, "type":"Feature"},
                buffer_size)
        return pnt.buffer(buffer_size).bounds
