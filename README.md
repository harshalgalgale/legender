# Legender

A tool for creating "thumbnail" images from WMS service layers for those
overcomplicated SLDs that cannot be used sensibly in OGC WMS GetLegendGraphic
requests.

Ideal for use with [GeoServer](http://geoserver.org/)

## Rationale

OGC WMS supports a GetLegendGraphic request which yields a layer legend based
on it's style description. But in case of more complicated styling (e.g.
using [GeoServer](http://geoserver.org/)'s [`Recode` function](http://docs.geoserver.org/stable/en/user/styling/sld/tipstricks/transformation-func.html#transformation-func),
or multilayering for a halo effect) this will not work. It would be possible to
produce the needed thumbnails by hand, but that seems like a tedious job if
there's many layers and those thumbnails need to be updated at any time.
Therefore the obvious solution would be to use an automated approach and let the
WMS service itself produce the legend images (thumbnails).

## How (is) it (supposed to) work?

Short answer: heavy use of configuration :)

Legender works based on WFS and WMS endpoints. WFS is used for querying for
a location where a feature on that layer is situated, and that
location in turn is used to do a WMS GetMap request to get a representative
image. The layer is scanned for different geometric primitives (points,
linestrings and polygons) separately so at most a 3-thumbnail legend image
will be produced for the layer. Additional filtering can also be done (e.g. for
`Recode`).

For example, this snippet of configuration for a fictitious layer called
`black:magic` (check out the
[full configuration example](#full-configuration-example)):

```
{
    "black:magic": [
        {
            "filter": "aCQLFilterFunction(expression)='foo'"
        },
        {
            "filter": "aCQLFilterFunction(expression)='bar'"
        }
    ]
}
```

will supplement the two resulting GetMap requests with
`...&request=GetMap&cql_filter=aCQLFilterFunction(expression)='foo'&...` and
`...&request=GetMap&cql_filter=aCQLFilterFunction(expression)='bar'&...`.

By default only the default style associated with the layer is used, but there's
support for querying specific styles or all styles:

```
{
    "black:magic": [
        {
            "styles": ["this","is", "a list of", "stylenames", "to use"]
        }
    ]
}
```

But there's no WFS enabled for this layer! No worries. Layer thumbnails can be
created by preset bounding box values aswell. Meaning you can tell Legender
that you want images from this-and-this layer at a particular bounding box:

```
{
    "black:magic": [
        {
            "bbox": [1, 2, 3, 4],
            "srs": "EPSG:something-something"
        }
    ]
}
```

@TODO: expand on other config issues.

## Full configuration example

@TODO

## Gotcha's

@TODO
