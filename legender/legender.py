# -*- coding: utf-8 -*-
import argparse, json, os, requests

from PIL import Image, ImageDraw, ImageOps, ImageFont
from StringIO import StringIO
from shapely.geometry import asShape, Point, LineString
import textwrap

class GeoServer(object):
    def __init__(self, url, **kwargs):
        self.session = requests.Session()
        if "username" in kwargs and kwargs['username'] != None:
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
        style='default', size=(100, 100), geometrytype_filtering=True,
        bckground_conf=None):
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
        if bckground_conf != None:
            data = self.get_background(bckground_conf, srs, bbox, size)
            bck = Image.open(StringIO(data))
        else:
            bck = None
        #bck.convert('RGBA')
        #print bck.mode, img.mode
        #bck.convert('RGBA')
        #bck.paste(img, (0, 0), img)
        #return bck
        return img, bck

    def get_background(self, bckground_conf, srs, bbox, size):
        #url = 'http://kaart.maaamet.ee/wms/fotokaart'
        width, height = size
        url = bckground_conf['url']
        layers = bckground_conf['layers']
        params = {
            "layers": layers,
            "service":"WMS",
            "version":"1.1.1",
            "format":"image/jpeg",
            "request":"GetMap",
            "srs":srs,
            "bbox":','.join(['%s' % coord for coord in bbox]),
            "width":width,
            "height":height,
            "transparent":True
        }
        r = requests.get(
            url,
            params=params
        )
        print r.url
        r.raise_for_status()
        return r.content


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
            format='image/png',
            #bgcolor='0xF9F5F4'
            bgcolor='0xffffff'

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
            print r.url
            return fn
        except Exception as e:
            raise ValueError(
                'Tried to get requests.%s from %s, instead got gibberish.' % (
                    returns, r.url
                ))
        return response


class Legend(object):
    font = '/usr/share/fonts/truetype/oxygen/Oxygen-Sans-Bold.ttf'
    def __init__(self, cls, url, layername=None, conf={}, **kwargs):
        self._gutter = 10
        self._size = (100, 100)
        self._thumbs = []
        self.server = cls(url, **kwargs)
        self.update_conf(layername, conf)

    def update_conf(self, layername, conf):
        self.layername = layername
        self.title = conf.get('title', layername)
        self.styles = conf.get('styles', ['default'])
        self.filter = conf.get('filter', None)
        self.bbox = conf.get('bbox', None)
        self.srs = conf.get('srs', None)
        # NB! srs needs to be set in any case!
        # unless we dive into WMS Capabilities, brrrrr....
        self.filename = conf.get('filename', None)
        self.whole_feature = conf.get('whole_feature', True)
        self.background = conf.get('background', None)

    def create_thumbnails(self, add_label=False):
        """Get and merge thumbnails for this configuration.

        Do styling things here aswell (e.g. add titles and whatnot)
        """
        _filter = self.filter or ''
        _filename = self.filename or _filter[:100]
        for stylename in self.styles:
            parts = [
                ''.join([s for s in self.layername if s not in ';:.,_']),
                ''.join([s for s in _filename if s not in ';:.,"\'_ ']),
                ''.join([s for s in stylename if s not in ';:.,_'])
            ]
            filename = '%s.png' % ('__'.join([p for p in parts if p != '']), )
            thumbs = []
            for geometrytype in ['Point', 'LineString', 'Polygon']:
                try:
                    thumb, bck = self._create_thumbnail(
                        stylename, geometrytype, self.filter
                    )
                except AssertionError as ae:
                    pass
                else:
                    if not self.is_empty_image(thumb):
                        if bck != None:
                            bck.paste(thumb, (0,0), thumb)
                            thumb = bck
                        thumb = self.apply_mask(thumb)
                        thumbs.append(thumb)
            img = self.merge_thumbnails(thumbs, add_label)
            if img != None:
                #img.save(os.path.join(path, filename), "PNG")
                self._thumbs.append({filename:img})

    def save(self, path, filename=None, title=None, group=False):
        if len(self._thumbs) == 0:
            return
        if group == False:
            for d in self._thumbs:
                filename = d.keys()[0]
                thumb = d.values()[0]
                if title != None:
                    thumb = self.merge_thumbnails(
                        [thumb], stack='vertical',
                        add_label=True, labeltext=title)
                thumb.save(os.path.join(path, filename))
        else:
            _thumbs = []
            for d in self._thumbs:
                _thumbs.append(d.values()[0])
            has_label = title != None
            img = self.merge_thumbnails(_thumbs, stack='vertical',
                add_label=has_label, labeltext=title)
            img.save(os.path.join(path, filename), "PNG")

    def apply_mask(self, thumb):
        """Make thumbnail round (that's all hip now, ain't it?), add outline."""
        width, height = thumb.size
        # antialias
        bigsize = (width * 4, height * 4)
        linewidth = 4
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

    def draw_label(self, img, location, label, size,
        fontsize=26, wraplength=30, stack='horizontal'):
        assert stack in ['horizontal', 'vertical']
        x, y = location
        width, height = img.size
        n = len(label)
        w, h = size

        font = ImageFont.truetype(self.font, fontsize)
        draw = ImageDraw.Draw(img)
        if stack == 'horizontal':
            pad_top = (height - h) / 2
            y = pad_top
        for line in label:
            #print w, h, x, y, '-->', line
            draw.text((x, y), line, (27, 29, 28, 255), font=font)
            y += h / n

    def calc_label_size(self, img, label, fontsize, wraplength):
        max_word = max([len(s) for s in label.split(' ')])
        if wraplength < max_word:
            wraplength = max_word
        label = textwrap.wrap(label, wraplength)
        font = ImageFont.truetype(self.font, fontsize)
        draw = ImageDraw.Draw(img)
        wh = [draw.textsize(line, font) for line in label]
        w = max([size[0] for size in wh])
        h = sum([size[1] for size in wh])
        return label, w, h

    def merge_thumbnails(self, thumbs=[], add_label=False, labeltext=None,
        stack='horizontal'):
        """Merge getmap thumbnails into one image."""
        assert stack in ['horizontal', 'vertical']
        n = len(thumbs)
        if n == 0:
            return
        gutter = self._gutter
        if stack == 'horizontal':
            w = sum([t.width for t in thumbs])
            h = max([t.height for t in thumbs])
            width, height = (w + gutter * n + gutter, h + gutter * 2)
        else:
            w = max([t.width for t in thumbs])
            h = sum([t.height for t in thumbs])
            width, height = (w + gutter * 2, h + gutter * n + gutter)
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        x, y = (gutter, gutter)
        for i, thumb in enumerate(thumbs):
            if stack == 'horizontal':
                location = (x, gutter)
                x += thumb.width + gutter
            else:
                location = (gutter, y)
                y += thumb.height + gutter
            img.paste(thumb, location)
        if add_label == True:
            labeltext = labeltext or self.title
            label, label_width, label_height = self.calc_label_size(
                img, labeltext, fontsize=26, wraplength=30)
            labelsize = (label_width, label_height)
            if stack == 'horizontal':
                new_width = label_width + x + gutter
                if label_height + (2 * gutter) > img.height:
                    height = img.height + (label_height - img.height) + 2 * gutter
                location = (x, y)
                _img = Image.new("RGBA", (new_width, height), (255, 255, 255, 255))
                _img.paste(img, (0, 0), img)
                self.draw_label(
                    _img, location, label, labelsize, stack=stack)
            else:
                new_height = label_height + y + gutter
                if label_width + (2 * gutter) > img.width:
                    width = img.width + (label_width - img.width) + 2 * gutter
                location = (gutter, gutter)
                _img = Image.new("RGBA", (width, new_height), (255, 255, 255, 255))
                _img.paste(img, (0, label_height + gutter), img)
                labelsize = (label_width, label_height)
                self.draw_label(
                    _img, location, label, labelsize, stack=stack)
            img = _img
        return img

    def _create_thumbnail(self, stylename, geometrytype, additional_filter):
        """Get image data and make a thumbnail for a layer for this style and
        geometry_type.
        """
        size = self._size
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
        transparent = self.background != None
        return self.server.get_map(self.layername, geometrytype, geometry_name,
            bbox, self.srs,
            transparent=transparent, additional_filter=additional_filter, featureid=None,
            style=stylename, size=size, bckground_conf=self.background)

    def get_bbox_from_feature(self, feature, buffer_size=500):
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
            if self.whole_feature != True:
                b = shape.boundary
                bbox = b.bounds
                bbox_width = bbox[2] - bbox[0]
                bbox_height = bbox[3] - bbox[1]
                if bbox_width < buffer_size * 2 and bbox_height < buffer_size * 2:
                    self.whole_feature = True
                else:
                    return self.get_bbox_from_feature(
                        {"geometry": b.__geo_interface__, "type":"Feature"},
                        buffer_size)
            if self.whole_feature == True:
                pnt, buffer_size = self._get_bbox_from_feature(shape)
        elif geometry_type.startswith('Multi'):
            if self.whole_feature == True:
                pnt, buffer_size = self._get_bbox_from_feature(shape)
            else:
                # HA-HA-HA :D
                # what the ???
                geom = shape.geoms[0]
                return self.get_bbox_from_feature(
                    {"geometry": geom.__geo_interface__, "type":"Feature"},
                    buffer_size)
        return pnt.buffer(buffer_size).bounds

    def _get_bbox_from_feature(self, shape):
        pnt = shape.centroid
        _, _, xmax, ymax = shape.bounds
        buffer_size = LineString([pnt, Point(xmax, ymax)]).length
        buffer_size *= 1.2
        return pnt, buffer_size

def run(conf_file_path):
    p, f = os.path.split(conf_file_path)
    if os.path.exists(p):
        os.chdir(p)
    with open(f) as _c:
        conf = json.loads(_c.read())
        for server, serverconf in conf.items():
            layers = serverconf.get('layers', [])
            background = serverconf.get('background', None)
            out_path = os.path.realpath(serverconf.get('out_path', '.'))
            username = conf.get('auth', {}).get('username', None)
            password = conf.get('auth', {}).get('password', None)
            add_labels = serverconf.get('add_labels', True)
            assert os.path.exists(out_path), "out_path %s does not exist" % (
                out_path, )
            for layer in layers:
                for layername, c in layer.items():
                    filters = c.get('filters', [])
                    title = c.get('title', None)
                    group = c.get('group', False)
                    filename = '%s.png' % (c.get('filename', layername), )
                    l = Legend(
                        GeoServer, server,
                        username=username, password=password)
                    for filterconf in filters:
                        if background.get('use', True) == True:
                            filterconf['background'] = background.copy()
                        l.update_conf(layername, filterconf)
                        l.create_thumbnails(add_labels)
                    l.save(out_path, filename.lower(), title, group)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate map legend thumbnails.')
    parser.add_argument('-c', type=str, help="Path to the configuration file")
    args = parser.parse_args()
    conf_file_path = args.c
    run(conf_file_path)
