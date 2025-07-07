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
        self.type = None
        self.layers = dict()

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
            self.layers[l.GetName()] = {
                "featurecount": len(l),
                "projection": proj,
                "bbox": l.GetExtent(),
            }
        ds = None
