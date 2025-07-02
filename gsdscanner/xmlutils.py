#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree

def getelemat(xml: etree._ElementTree, path: str, nsmap=None):
    r = xml.xpath(path, namespaces=nsmap)
    if len(r) > 0:
        return r[0].text
    return None
