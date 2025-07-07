#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from geordash.utils import getelemat

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
        self.collections = dict()
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
        self.version = getelemat(tree, "/global/updateSequence")

    def parse(self, toparse):
        print(f"parse({toparse})")
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
        self.parse(self.available_keys)
