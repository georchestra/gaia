#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from glob import glob

# from .workspace import Workspace


class Collection:
    def __init__(self, glob, objtype):
        self.glob = glob
        self.type = objtype
        self.coll = dict()
        self.list()

    def __repr__(self):
        return f"{self.type}: glob={self.glob}, entries={len(self.coll)}"

    def list(self):
        if type(self.glob) == list:
            files = sum([glob(x, recursive="**" in x) for x in self.glob], [])
        else:
            files = glob(self.glob, recursive="**" in self.glob)
        for f in files:
            e = self.type(f)
            e.parse()
            self.coll[e.id] = e

    def len(self):
        return len(self.coll)

    def has(self, key):
        return key in self.coll
