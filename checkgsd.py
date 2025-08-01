#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from os.path import dirname
from gsdscanner import GSDatadirScanner
from geordash.utils import find_geoserver_datadir
from geordash.checks.gsd import gsdatadir_item

gds = GSDatadirScanner(find_geoserver_datadir('/data/webapps/geoserver'))
print(f"datadir version: {gds.version}")
gds.parseAll()
for colltype in gds.available_keys:
    for k in gds.collections[colltype].coll:
        ret = gsdatadir_item(colltype, k, gsd=gds)
        if len(ret['problems']) > 0:
            print(f"{colltype} {k} -> {ret['problems']}")

# check for RasterData/VectorData
# for Vector:
# if shapefile:
#   look for a type=ShapeFile datastore pointing at the parent folder
#   or a 'directory of spatial files (shapefiles) datastore pointing at the parent folder (connectionParameters, entry key=url)
#   then featuretype.xml/nativeName=shapefile name in folder ?
# if *.gpkg:
#  look for a type=GeoPackage datastore with connectionParameters/entry[name=database] pointing at the geopackage file
#   then featuretype.xml/nativeName=layer name in the geopackage
# for Raster:
# look for a CoverageStore type=GeoTIFF pointing at the relative path
# or a CoverageStore type=ImageMosaic pointing at the parent folder, folder should have a VectorData/tileindex with a feature pointing a the raster

# check that all layers appear in a wms getcap
