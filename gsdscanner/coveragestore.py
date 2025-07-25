#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from geordash.utils import getelemat


class Coveragestore(dict):
    def __init__(self, xmlf):
        self.file = xmlf

    def __repr__(self):
        return f"Coveragestore: file={self.file}, id={self.id}, name={self.name}, type={self.type}, workspaceid={self.workspaceid}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, "/coverageStore/id")
        self.name = getelemat(xml, "/coverageStore/name")
        self.type = getelemat(xml, "/coverageStore/type")
        self.enabled = getelemat(xml, "/coverageStore/enabled")
        self.workspaceid = getelemat(xml, "/coverageStore/workspace/id")
        self.url = getelemat(
            xml, "/coverageStore/url"
        )  # path (relative to datadir) to tif or folder for type=imagemosaic ?
