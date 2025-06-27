#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import requests
from lxml import etree
from geordash.utils import getelemat


def parse_map(xmlstring):
    nsmap = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    details = dict()
    # XXX handle parse errors
    xml = etree.fromstring(bytes(xmlstring, encoding="utf-8"))
    details["title"] = getelemat(
        xml, "/config/metadata/rdf:RDF/rdf:Description/dc:title", nsmap=nsmap
    )
    if details["title"] == None:
        app = xml.xpath("/config/application", namespaces=nsmap)
        if app and len(app) > 0:
            details["title"] = app[0].attrib["title"]

    if len(xml.xpath("/config/metadata")) > 0:
        details["dc"] = dict()
        details["dc"]["date"] = getelemat(
            xml, "/config/metadata/rdf:RDF/rdf:Description/dc:date", nsmap=nsmap
        )
        details["dc"]["creator"] = getelemat(
            xml, "/config/metadata/rdf:RDF/rdf:Description/dc:creator", nsmap=nsmap
        )
        details["dc"]["subject"] = [ele.text for ele in xml.xpath(
            "/config/metadata/rdf:RDF/rdf:Description/dc:subject", namespaces=nsmap
        )]
    layers = list()
    baselayers = list()
    for l in xml.xpath(
        "|".join(
            [
                "/config/baselayers/baselayer",
                "/config/themes/theme/group/layer",
                "/config/themes/theme/layer",
            ]
        ),
        namespaces=nsmap,
    ):
        if "type" in l.attrib and l.attrib["type"].lower() not in [
            "wms",
            "wmts",
            "wfs",
        ]:
            continue
        url = l.attrib["url"]
        if "type" in l.attrib:
            stype = l.attrib["type"]
        else:
            # if unset, layer type is wms
            stype = "wms"
        layername = l.attrib["id"]
        if "secure" in l.attrib and (
            l.attrib["secure"] == "layer" or l.attrib["secure"] == "global"
        ):
            # layer not public, ignoring
            continue
        if l.tag == "layer":
            tpl = l.find('./template')
            tplurl = None
            if tpl is not None and "url" in tpl.attrib:
                tplurl = tpl.attrib["url"]
            styles = list()
            if "sld" in l.attrib and l.attrib["sld"] != "":
                styles = [s.lstrip() for s in l.attrib["sld"].split(",")]
            layers.append(
                {
                    "type": stype,
                    "url": url,
                    "name": layername,
                    "title": l.attrib.get("name"),
                    "styles": styles,
                    "templateurl": tplurl
                }
            )
        else:
            baselayers.append(
                {
                    "type": stype,
                    "url": url,
                    "name": layername,
                    "title": l.attrib.get("label"),
                }
            )

    # TODO:
    # csw links

    details["layers"] = layers
    details["baselayers"] = baselayers
    return details
