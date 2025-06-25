#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from .xmlutils import getelemat

class FeatureType(dict):
    def __init__(self, xmlf):
        self.file = xmlf

    def __repr__(self):
        return f"FeatureType: file={self.file}, id={self.id}, name={self.name}, title={self.title}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, '/featureType/id')
        self.name = getelemat(xml, '/featureType/name')
        self.title = getelemat(xml, '/featureType/title')
        self.declaredsrs = getelemat(xml, '/featureType/srs')
        self.advertised = getelemat(xml, '/featureType/advertised')
        if self.advertised is None:
            self.advertised = 'true'
        self.enabled = getelemat(xml, '/featureType/enabled')
        if self.enabled is None:
            self.enabled = 'true'
        self.namespaceid = getelemat(xml, '/featureType/namespace/id')
        self.datastoreid = getelemat(xml, '/featureType/store/id')
        # XXX metadataLinks
