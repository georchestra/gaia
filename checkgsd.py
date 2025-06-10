#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from os.path import dirname
from gsdscanner import GSDatadirScanner
from geordash.utils import find_geoserver_datadir

gds = GSDatadirScanner(find_geoserver_datadir('/data/webapps/geoserver'))
print(f"datadir version: {gds.version}")
gds.parseAll()
for d in ('workspaces', 'datastores', 'namespaces', 'featuretypes', 'layers', 'styles', 'slds', 'vectordatas', 'rasterdatas'):
    for e in gds.collections[d].coll:
        print(f"{e} -> {gds.collections[d].coll[e]}")

for e in gds.collections['datastores'].coll:
    ds = gds.collections['datastores'].coll[e]
    assert gds.collections['workspaces'].has(ds.workspaceid)
print(f"checked {len(gds.collections['datastores'].coll)} datastores")

for e in gds.collections['coveragestores'].coll:
    cs = gds.collections['coveragestores'].coll[e]
    assert gds.collections['workspaces'].has(cs.workspaceid)
print(f"checked {len(gds.collections['coveragestores'].coll)} coveragestores")

for e in gds.collections['featuretypes'].coll:
    ft = gds.collections['featuretypes'].coll[e]
    assert gds.collections['datastores'].has(ft.datastoreid)
    assert gds.collections['namespaces'].has(ft.namespaceid)
    # if datastore is of type JNDI, look for a table name matching nativeName in the linked postgis JNDI cnx

print(f"checked {len(gds.collections['featuretypes'].coll)} featuretypes")

for e in gds.collections['layers'].coll:
    l = gds.collections['layers'].coll[e]
    if l.featuretypeid.startswith('FeatureTypeInfoImpl'):
        assert gds.collections['featuretypes'].has(l.featuretypeid)
    elif l.featuretypeid.startswith('CoverageInfoImpl'):
        assert gds.collections['coverages'].has(l.featuretypeid)
print(f"checked {len(gds.collections['layers'].coll)} layers")

for e in gds.collections['slds'].coll:
    s = gds.collections['slds'].coll[e]
    if s.filesize <= 0:
        print(f"{s.file} is empty")
print(f"checked {len(gds.collections['slds'].coll)} slds")

for e in gds.collections['styles'].coll:
    s = gds.collections['styles'].coll[e]
    if '/workspaces/' in s.file:
        assert gds.collections['workspaces'].has(s.workspaceid)
    else:
        assert s.workspaceid == None
    # check that sldfilename relative to style exists XXX doesnt handle css styles yet
    sldpath = dirname(s.file) + '/' + s.sldfilename
    if not gds.collections['slds'].has(sldpath) and not sldpath.endswith('.css'):
        print(f"{sldpath} not found")
print(f"checked {len(gds.collections['styles'].coll)} styles")

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
