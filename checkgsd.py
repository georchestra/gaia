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
