#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from geordash.utils import getelemat


class Coverage(dict):
    def __init__(self, xmlf):
        self.file = xmlf

    def __repr__(self):
        return f"Coverage: file={self.file}, id={self.id}, name={self.name}, title={self.title}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, "/coverage/id")
        self.name = getelemat(xml, "/coverage/name")
        self.nativeName = getelemat(xml, "/coverage/nativeName")
        self.title = getelemat(xml, "/coverage/title")
        self.declaredsrs = getelemat(xml, "/coverage/srs")
        self.namespaceid = getelemat(xml, "/coverage/namespace/id")
        self.coveragestoreid = getelemat(xml, "/coverage/store/id")
        # XXX metadataLinks
