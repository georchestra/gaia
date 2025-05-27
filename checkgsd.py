#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from gsdscanner import GSDatadirScanner

gds = GSDatadirScanner('/data/webapps/geoserver')
print(f"datadir version: {gds.version}")
gds.parseAll()
for d in ('workspaces', 'datastores', 'namespaces', 'featuretypes'):
    for e in gds.collections[d].coll:
        print(f"{e} -> {gds.collections[d].coll[e]}")

for e in gds.collections['datastores'].coll:
    ds = gds.collections['datastores'].coll[e]
    assert gds.collections['workspaces'].has(ds.workspaceid)
print(f"checked {len(gds.collections['datastores'].coll)} datastores")

for e in gds.collections['featuretypes'].coll:
    ft = gds.collections['featuretypes'].coll[e]
    assert gds.collections['datastores'].has(ft.datastoreid)
    assert gds.collections['namespaces'].has(ft.namespaceid)

print(f"checked {len(gds.collections['featuretypes'].coll)} featuretypes")
