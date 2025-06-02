#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from .xmlutils import getelemat

from .workspace import Workspace
from .datastore import Datastore
from .namespace import Namespace
from .featuretype import FeatureType
from .coveragestore import Coveragestore
from .coverage import Coverage
from .layer import Layer
from .style import Style
from .sld import SLD
from .collection import Collection

class GSDatadirScanner:
    def __init__(self, path='/srv/data/geoserver'): # default path for ansible deployments
        self.basepath = path
        self.collections = dict()
        # XXX handle access errors re ownership/rights
        tree = etree.parse(f'{path}/global.xml')
        self.pburl = getelemat(tree, '/global/settings/proxyBaseUrl')
        self.version = getelemat(tree, '/global/updateSequence')

    def parseAll(self):
        self.collections['workspaces'] = Collection(f"{self.basepath}/workspaces/*/workspace.xml", Workspace)
        self.collections['datastores'] = Collection(f"{self.basepath}/workspaces/*/*/datastore.xml", Datastore)
        self.collections['coveragestores'] = Collection(f"{self.basepath}/workspaces/*/*/coveragestore.xml", Coveragestore)
        self.collections['namespaces'] = Collection(f"{self.basepath}/workspaces/*/namespace.xml", Namespace)
        self.collections['featuretypes'] = Collection(f"{self.basepath}/workspaces/*/*/*/featuretype.xml", FeatureType)
        self.collections['coverages'] = Collection(f"{self.basepath}/workspaces/*/*/*/coverage.xml", Coverage)
        self.collections['layers'] = Collection(f"{self.basepath}/workspaces/*/*/*/layer.xml", Layer)
        self.collections['styles'] = Collection([f"{self.basepath}/styles/*.xml", f"{self.basepath}/workspaces/*/styles/*.xml"], Style)
        self.collections['slds'] = Collection([f"{self.basepath}/styles/*.sld", f"{self.basepath}/workspaces/*/styles/*.sld"], SLD)
        # XXX pour geodata *.shp, *.gpkg & *.tif avec find -iname ?
