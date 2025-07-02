#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from .xmlutils import getelemat

class Namespace(dict):
    def __init__(self, xmlf):
        self.file = xmlf

    def __repr__(self):
        return f"Namespace: file={self.file}, id={self.id}, name={self.name}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, '/namespace/id')
        self.name = getelemat(xml, '/namespace/prefix')
        self.uri = getelemat(xml, '/namespace/uri')
