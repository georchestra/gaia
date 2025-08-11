#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from geordash.utils import getelemat


class FeatureType(dict):
    def __init__(self, xmlf):
        self.file = xmlf
        self.nativename = None
        self.referenced_by = set()

    def __repr__(self):
        return f"FeatureType: file={self.file}, id={self.id}, name={self.name}, title={self.title}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, "/featureType/id")
        self.name = getelemat(xml, "/featureType/name")
        self.title = getelemat(xml, "/featureType/title")
        self.declaredsrs = getelemat(xml, "/featureType/srs")
        self.advertised = getelemat(xml, "/featureType/advertised")
        if self.advertised is None:
            self.advertised = "true"
        self.enabled = getelemat(xml, "/featureType/enabled")
        if self.enabled is None:
            self.enabled = "true"
        self.namespaceid = getelemat(xml, "/featureType/namespace/id")
        self.datastoreid = getelemat(xml, "/featureType/store/id")
        self.nativename = getelemat(xml, "/featureType/nativeName")
        self.metadatalinks = None
        r = xml.xpath("/featureType/metadataLinks/metadataLink")
        if len(r) > 0:
            self.metadatalinks = list()
            for e in r:
                mdformat = e.find("type").text
                mdtype = e.find("metadataType").text
                mdurl = e.find("content").text
                self.metadatalinks.append(
                    {"format": mdformat, "type": mdtype, "url": mdurl}
                )
