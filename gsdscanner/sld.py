#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from os.path import getsize
from lxml import etree
from lxml.etree import XMLParser
from .xmlutils import getelemat


class SLD(dict):
    def __init__(self, xmlf):
        self.file = xmlf
        self.filesize = getsize(xmlf)
        self.id = self.file
        self.name = None
        self.firstrulename = None

    def __repr__(self):
        return f"SLD: file={self.file}, id={self.id}, name={self.name}"

    def parse(self):
        # check for empty sld, only parse if not empty..
        if self.filesize > 0:
            try:
                xml = etree.parse(self.file)
            except etree.XMLSyntaxError:
                # try harder to handle malformed xml
                xml = etree.parse(self.file, parser=XMLParser(recover=True))
            nsmap = {
                "sld": "http://www.opengis.net/sld",
                "se": "http://www.opengis.net/se",
            }
            self.name = getelemat(
                xml,
                "|".join(
                    [
                        "/sld:StyledLayerDescriptor/sld:NamedLayer/sld:Name",
                        "/StyledLayerDescriptor/NamedLayer/se:Name",
                        "/StyledLayerDescriptor/NamedLayer/Name",
                        "/StyledLayerDescriptor/UserLayer/Name",
                        "/sld:UserStyle/sld:Name",
                    ]
                ),
                nsmap=nsmap,
            )
            self.firstrulename = getelemat(
                xml,
                "|".join(
                    [
                        "(/sld:StyledLayerDescriptor/sld:NamedLayer/sld:UserStyle/sld:FeatureTypeStyle/sld:Rule)[1]/sld:Name",
                        "(/StyledLayerDescriptor/NamedLayer/UserStyle/se:FeatureTypeStyle/se:Rule)[1]/se:Name",
                        "(/StyledLayerDescriptor/NamedLayer/UserStyle/FeatureTypeStyle/Rule)[1]/Name",
                        "(/sld:UserStyle/sld:FeatureTypeStyle/sld:Rule)[1]/sld:Title",
                    ]
                ),
                nsmap=nsmap,
            )
