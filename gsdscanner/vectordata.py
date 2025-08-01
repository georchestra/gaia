#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from os.path import getsize
from osgeo.ogr import Open


class VectorData(dict):
    def __init__(self, path):
        self.file = path
        self.filesize = getsize(path)
        self.id = self.file.replace("/", "~")
        if self.id.endswith(".SHP"):
            # dont use replace() as SHP might be present in the path..
            self.id = self.id.removesuffix(".SHP") + ".shp"
        self.type = None
        self.layers = dict()
        self.referenced_by = set()

    def __repr__(self):
        return f"VectorData: id={self.id}, type={self.type}, layers={self.layers}"

    def parse(self):
        ds = Open(self.file)
        if ds is None:
            return
        self.type = ds.GetDriver().GetName()
        for l in ds:
            sr = l.GetSpatialRef()
            proj = None
            if sr is not None:
                proj = sr.GetName()
            ldefn = l.GetLayerDefn()
            fields = list()
            for n in range(ldefn.GetFieldCount()):
                fdefn = ldefn.GetFieldDefn(n)
                fields.append(fdefn.name)
            self.layers[l.GetName()] = {
                "featurecount": len(l),
                "fields": fields,
                "projection": proj,
                "bbox": l.GetExtent(),
            }
        ds = None
