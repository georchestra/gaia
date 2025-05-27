#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from .xmlutils import getelemat

from .workspace import Workspace
from .datastore import Datastore
from .namespace import Namespace
from .featuretype import FeatureType
from .layer import Layer
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
        self.collections['namespaces'] = Collection(f"{self.basepath}/workspaces/*/namespace.xml", Namespace)
        self.collections['featuretypes'] = Collection(f"{self.basepath}/workspaces/*/*/*/featuretype.xml", FeatureType)
        self.collections['layers'] = Collection(f"{self.basepath}/workspaces/*/*/*/layer.xml", Layer)
