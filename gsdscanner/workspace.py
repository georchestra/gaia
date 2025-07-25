#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from geordash.utils import getelemat


class Workspace(dict):
    def __init__(self, xmlf):
        self.file = xmlf

    def __repr__(self):
        return f"Workspace: file={self.file}, id={self.id}, name={self.name}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, "/workspace/id")
        self.name = getelemat(xml, "/workspace/name")
