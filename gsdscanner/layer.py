#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from .xmlutils import getelemat

class Layer:
    def __init__(self, xmlf):
        self.file = xmlf
        self.parse()

    def __repr__(self):
        return f"Layer: file={self.file}, id={self.id}, name={self.name}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, '/layer/id')
        self.name = getelemat(xml, '/layer/name')
        self.type = getelemat(xml, '/layer/type')
        self.defaultstyleid = getelemat(xml, '/layer/defaultStyle/id')
        self.featuretypeid = getelemat(xml, '/layer/resource/id')
        # XXX styles at /layer/styles/style/id
