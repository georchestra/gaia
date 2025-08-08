#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from datetime import datetime
from osgeo.ogr import Open
import os
from geordash.utils import getelemat
from geordash.logwrap import get_logger

from .workspace import Workspace
from .datastore import Datastore
from .namespace import Namespace
from .featuretype import FeatureType
from .coveragestore import Coveragestore
from .coverage import Coverage
from .layer import Layer
from .style import Style
from .sld import SLD
from .vectordata import VectorData
from .rasterdata import RasterData
from .collection import Collection


class GSDatadirScanner:
    def __init__(
        self, path="/srv/data/geoserver"
    ):  # default path for ansible deployments
        self.basepath = path
        self.parsed = False
        self.collections = dict()
        # XXX handle layergroups
        self.available_keys = [
            "workspaces",
            "datastores",
            "coveragestores",
            "namespaces",
            "featuretypes",
            "coverages",
            "layers",
            "styles",
            "slds",
            "vectordatas",
            "rasterdatas",
        ]
        # XXX handle access errors re ownership/rights
        tree = etree.parse(f"{path}/global.xml")
        self.pburl = getelemat(tree, "/global/settings/proxyBaseUrl")
        self.version = int(getelemat(tree, "/global/updateSequence"))

    def parse(self, toparse):
        if type(toparse) == list:
            for i in toparse:
                self.parse(i)
        else:
            match toparse:
                case "workspaces":
                    self.collections["workspaces"] = Collection(
                        f"{self.basepath}/workspaces/*/workspace.xml", Workspace
                    )
                case "datastores":
                    self.collections["datastores"] = Collection(
                        f"{self.basepath}/workspaces/*/*/datastore.xml", Datastore
                    )
                case "coveragestores":
                    self.collections["coveragestores"] = Collection(
                        f"{self.basepath}/workspaces/*/*/coveragestore.xml",
                        Coveragestore,
                    )
                case "namespaces":
                    self.collections["namespaces"] = Collection(
                        f"{self.basepath}/workspaces/*/namespace.xml", Namespace
                    )
                case "featuretypes":
                    self.collections["featuretypes"] = Collection(
                        f"{self.basepath}/workspaces/*/*/*/featuretype.xml", FeatureType
                    )
                case "coverages":
                    self.collections["coverages"] = Collection(
                        f"{self.basepath}/workspaces/*/*/*/coverage.xml", Coverage
                    )
                case "layers":
                    self.collections["layers"] = Collection(
                        f"{self.basepath}/workspaces/*/*/*/layer.xml", Layer
                    )
                case "styles":
                    self.collections["styles"] = Collection(
                        [
                            f"{self.basepath}/styles/*.xml",
                            f"{self.basepath}/workspaces/*/styles/*.xml",
                        ],
                        Style,
                    )
                case "slds":
                    self.collections["slds"] = Collection(
                        [
                            f"{self.basepath}/styles/*.sld",
                            f"{self.basepath}/workspaces/*/styles/*.sld",
                        ],
                        SLD,
                    )
                case "vectordatas":
                    self.collections["vectordatas"] = Collection(
                        [
                            f"{self.basepath}/data/**/{f}"
                            for f in ["*.shp", "*.SHP", "*.gpkg"]
                        ],
                        VectorData,
                    )
                case "rasterdatas":
                    self.collections["rasterdatas"] = Collection(
                        [f"{self.basepath}/data/**/{f}" for f in ["*.tif", "*.tiff"]],
                        RasterData,
                    )
                case _:
                    pass
                    ## XXX unreachable

    def parseAll(self):
        start = datetime.now()
        self.parse(self.available_keys)
        self.compute_crossref()
        end = datetime.now()
        get_logger("GsdScanner").debug(f"geoserver datadir parsing took {end-start}")
        self.parsed = True

    def compute_crossref(self):
        """compute cross references between xml files, and data files

        - datastore -> workspace & vectordata for geopackage
        - coveragestore -> workspace & rasterdata for geotiff
        - coverage -> coveragestore, rasterdata for geotiff, rasterdata & vectordata for ImageMosaic
        - featuretype -> datastore & vectordata
        - layer -> {featuretype, coverage} + style
        - style -> sld
        """
        for d in self.collections["datastores"].coll.values():
            w = self.collections["workspaces"].coll.get(d.workspaceid)
            if w is not None:
                w.referenced_by.add(("datastore", d.id))
            if d.connurl is not None and d.type == "GeoPackage":
                vdk = d.connurl.replace("/", "~")
                vd = self.collections["vectordatas"].coll.get(vdk)
                if vd is not None:
                    vd.referenced_by.add(("datastore", d.id))

        for c in self.collections["coveragestores"].coll.values():
            w = self.collections["workspaces"].coll.get(c.workspaceid)
            if w is not None:
                w.referenced_by.add(("coveragestore", c.id))
            if os.path.isfile(c.url) and c.type == "GeoTiff":
                rdk = c.url.replace("/", "~")
                rd = self.collections["rasterdatas"].coll.get(rdk)
                if rd is not None:
                    rd.referenced_by.add(("coveragestore", c.id))

        for f in self.collections["featuretypes"].coll.values():
            ds = self.collections["datastores"].coll.get(f.datastoreid)
            if ds is not None:
                ds.referenced_by.add(("featuretype", f.id))
                if ds.type in [
                    "Shapefile",
                    "Directory of spatial files (shapefiles)",
                    "GeoPackage",
                ]:
                    fpath = ds.connurl
                    if "shapefile" in ds.type.lower():
                        if fpath.endswith("/"):
                            fpath = fpath.removesuffix("/")
                        fpath = f"{fpath}/{f.nativename}.shp"
                    vdk = fpath.replace("/", "~")
                    vd = self.collections["vectordatas"].coll.get(vdk)
                    if vd is not None:
                        vd.referenced_by.add(("featuretype", f.id))

        for c in self.collections["coverages"].coll.values():
            cs = self.collections["coveragestores"].coll.get(c.coveragestoreid)
            if cs is not None:
                cs.referenced_by.add(("coverage", c.id))
                if cs.type == "GeoTIFF":
                    rdk = cs.url.replace("/", "~")
                    rd = self.collections["rasterdatas"].coll.get(rdk)
                    if rd is not None:
                        rd.referenced_by.add(("coverage", c.id))
                elif cs.type == "ImageMosaic" and os.path.isdir(cs.url):
                    idx = cs.url
                    if idx.endswith("/"):
                        idx = idx.removesuffix("/")
                    idx = f"{idx}/{c.nativecoveragename}.shp"
                    # check that a shp exists with the same name
                    if os.path.isfile(idx):
                        vdk = idx.replace("/", "~")
                    vd = self.collections["vectordatas"].coll.get(vdk)
                    if vd is not None:
                        vd.referenced_by.add(("coverage", c.id))
                        if c.nativecoveragename in vd.layers and vd.layers[
                            c.nativecoveragename
                        ]["fields"] == ["location"]:
                            # iterate over features, check that each of them is an existing rd
                            ds = Open(vd.file)
                            l = ds.GetLayerByName(c.nativecoveragename)
                            for f in l:
                                rpath = f.GetField("location")
                                # if not absolute path, prepend the coveragestore url
                                if not rpath.startswith("/"):
                                    csdir = cs.url
                                    if csdir.endswith("/"):
                                        csdir = csdir.removesuffix("/")
                                    rpath = f"{csdir}/{rpath}"
                                if os.path.isfile(rpath):
                                    rdk = rpath.replace("/", "~")
                                    # check that it's an existing rd
                                    rd = self.collections["rasterdatas"].coll.get(rdk)
                                    if rd is not None:
                                        rd.referenced_by.add(("coverage", c.id))
                                        rd.referenced_by.add(("vectordatas", vd.id))

        for l in self.collections["layers"].coll.values():
            if l.coverageid:
                c = self.collections["coverages"].coll.get(l.coverageid)
                if c is not None:
                    c.referenced_by.add(("layer", l.id))
            if l.featuretypeid:
                ft = self.collections["featuretypes"].coll.get(l.featuretypeid)
                if ft is not None:
                    ft.referenced_by.add(("layer", l.id))
            st = self.collections["styles"].coll.get(l.defaultstyleid)
            if st is not None:
                st.referenced_by.add(("layer", l.id))
            if l.styleids:
                for sid in l.styleids:
                    st = self.collections["styles"].coll.get(sid)
                    if st is not None:
                        st.referenced_by.add(("layer", l.id))

        for s in self.collections["styles"].coll.values():
            if s.format == "sld":
                if os.path.isfile(s.sldpath):
                    sk = s.sldpath.replace("/", "~")
                    sld = self.collections["slds"].coll.get(sk)
                    if sld is not None:
                        sld.referenced_by.add(("style", s.id))
