#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from geordash.utils import getelemat


class Style(dict):
    def __init__(self, xmlf):
        self.file = xmlf
        self.referenced_by = set()

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
        # styles created before the introduction of css dont have a format tag
        if self.format is None:
            if getelemat(xml, "/style/sldVersion") is not None:
                self.format = 'sld'
            elif self.sldfilename.endswith('.sld'):
                # likely the default styles in the global ws
                self.format = 'sld'
