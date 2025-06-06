#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from os.path import getsize
from osgeo.gdal import Open

class RasterData:
    def __init__(self, path):
        self.file = path
        self.filesize = getsize(path)
        self.id = self.file
        self.projection = None
        self.bbox = None
        self.type = None
#        self.parse()

    def __repr__(self):
        return f"RasterData: type={self.type}, proj={self.projection}, bbox={self.bbox}"

    def parse(self):
        ds = Open(self.file)
        if ds is None:
            print(f"failed opening {self.file}")
            return
        self.type = ds.GetDriver().GetDescription()
        sr = ds.GetSpatialRef()
        if sr is not None:
            self.projection = sr.GetName()
            sr = None
        gt = ds.GetGeoTransform()
        xsize = ds.RasterXSize # Size in the x-direction
        ysize = ds.RasterYSize # Size in the y-direction
        xr = abs(gt[1]) # Resolution in the x-direction
        yr = abs(gt[-1]) # Resolution in the y-direction
        self.bbox = [gt[0], gt[3] - (ysize * yr), gt[0] + (xsize * xr), gt[3]]
        ds = None
