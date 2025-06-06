#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from .xmlutils import getelemat


class Style:
    def __init__(self, xmlf):
        self.file = xmlf

    def __repr__(self):
        return f"Style: file={self.file}, id={self.id}, name={self.name}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, "/style/id")
        self.name = getelemat(xml, "/style/name")
        # for now only sld
        self.format = getelemat(xml, "/style/format")
        # can be None for styles in the global workspace
        self.workspaceid = getelemat(xml, "/style/workspace/id")
        self.sldfilename = getelemat(xml, "/style/filename")
