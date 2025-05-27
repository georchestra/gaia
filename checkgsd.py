#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from gsdscanner import GSDatadirScanner

gds = GSDatadirScanner('/data/webapps/geoserver')
print(f"datadir version: {gds.version}")
gds.parseAll()
for d in ('workspaces', 'datastores', 'namespaces', 'featuretypes', 'layers'):
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

print(f"checked {len(gds.collections['featuretypes'].coll)} featuretypes")

for e in gds.collections['layers'].coll:
    l = gds.collections['layers'].coll[e]
    if l.featuretypeid.startswith('FeatureTypeInfoImpl'):
        assert gds.collections['featuretypes'].has(l.featuretypeid)
    elif l.featuretypeid.startswith('CoverageInfoImpl'):
        assert gds.collections['coverages'].has(l.featuretypeid)
print(f"checked {len(gds.collections['layers'].coll)} layers")

