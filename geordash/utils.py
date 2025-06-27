#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import current_app as app
from geordash.logwrap import get_logger
from lxml import etree

def getelemat(xml: etree._ElementTree, path: str, nsmap=None):
    r = xml.xpath(path, namespaces=nsmap)
    if len(r) > 0:
        return r[0].text
    return None

def find_localmduuid(service, layername):
    localmduuids = set()
    localdomain = "https://" + app.extensions["conf"].get("domainName")
    l = service.contents[layername]
    # wmts doesnt have metadataUrls
    if not hasattr(l, "metadataUrls"):
        return localmduuids
    for m in l.metadataUrls:
        mdurl = m["url"]
        mdformat = m["format"]
        if mdurl.startswith(localdomain):
            if mdformat == "text/xml" and "formatters/xml" in mdurl:
                # XXX find the uuid in https://geobretagne.fr/geonetwork/srv/api/records/60c7177f-e4e0-48aa-922b-802f2c921efc/formatters/xml
                localmduuids.add(mdurl.split("/")[7])
            if mdformat == "text/html" and "datahub/dataset" in mdurl:
                # XXX find the uuid in https://geobretagne.fr/datahub/dataset/60c7177f-e4e0-48aa-922b-802f2c921efc
                localmduuids.add(mdurl.split("/")[5])
            if mdformat == "text/html" and "api/records" in mdurl:
                # XXX find the uuid in https://ids.craig.fr/geocat/srv/api/records/9c785908-004d-4ed9-95a6-bd2915da1f08
                localmduuids.add(mdurl.split("/")[7])
            if mdformat == "text/html" and "catalog.search" in mdurl:
                # XXX find the uuid in https://ids.craig.fr/geocat/srv/fre/catalog.search#/metadata/e37c057b-5884-429b-8bec-5db0baef0ee1
                localmduuids.add(mdurl.split("/")[8])
    return localmduuids


def unmunge(url, prunefqdn=True):
    """
    takes a munged url in the form ~geoserver(|~ws)~ows or http(s):~~fqdn~geoserver(|~ws)~ows
    returns: a proper url with slashes, eventually stripped of the local ids domainName (eg /geoserver/ws/ows)
    """
    url = url.replace("~", "/")
    if not url.startswith("/") and not url.startswith("http"):
        url = "/" + url
    localdomain = "https://" + app.extensions["conf"].get("domainName")
    if url.startswith(localdomain) and prunefqdn:
        url = url.removeprefix(localdomain)
    if not url.startswith("http") and not url.startswith(localdomain) and not prunefqdn:
        url = localdomain + url
    return url


def objtype(o):
    """
    returns a string of the forme module.name for the given object
    better than str(type(o)) which returns "<class 'module.name'>"
    (which doesn't render properly as HTML..)
    """
    k = o.__class__
    return ".".join([k.__module__, k.__name__])


def normalize_gs_workspace_layer(url, layer=None):
    """
    normalize the various ways to address the same gs layer:
    - https://fqdn/wxs/wms -> /wxs/ows
    - /wxs/wms -> /wxs/ows
    - wxs/wfs -> /wxs/ows
    - /wxs/cd01/wfs, layer=foo -> /wxs/ows, layer=cd01:foo
    - /wxs/cd01/wms, layer=cd01:foo -> /wxs/ows, layer=cd01:foo
    - /wxs/wms, layer=cd01:foo -> /wxs/ows, layer=cd01:foo
    """

    localgsbaseurl = app.extensions["conf"].get("localgs", "urls")
    localdomain = "https://" + app.extensions["conf"].get("domainName")

    if url.startswith(localdomain):
        # strip localdomain from looked up url, should end up with /localgsbaseurl/<ws>/{ows,wms,wfs}
        url = url.removeprefix(localdomain)
    else:
        # if url doesnt start with localdomain or isnt a full url, ensure it starts with a leading / (shouldnt happen.. who knows)
        if (
            not url.startswith("https://")
            and not url.startswith("http://")
            and not url.startswith("/")
        ):
            url = "/" + url

    # are we talking to 'a geoserver' ?
    if "/" + localgsbaseurl + "/" in url:
        # account for the various ways to use geoserver (eg /ows, /wms, /wfs...)
        # and ensure the url finishes by /ows
        url = (
            url.removesuffix("/wms").removesuffix("/wfs").removesuffix("/ows") + "/ows"
        )
        # look for the workspace in the url, set the url to the global one and
        # put the workspace as a prefix of the layername
        if layer is not None and url.count("/") > 2:
            ourl = url
            # url like protocol://domain
            if url.startswith("https://") or url.startswith("http://"):
                parts = url.split("/")
                protocol = parts[0]
                fqdn = parts[2]
                # that's a full url with the workspace
                if url.count("/") == 5 and parts[5] == "ows":
                    ws = parts[4]
                else:
                    if ":" in layer:
                        ws = layer.split(":")[0]
                    else:
                        get_logger("CheckMapstore").debug(
                            f"havent been able to find workspace with url {url} and layer {layer}, returning as-is"
                        )
                        return (url, layer)
                url = f"{protocol}//{fqdn}/{localgsbaseurl}/ows"
            else:
                # url without protocol://domain
                ws = url.split("/")[2]
                url = "/" + localgsbaseurl + "/ows"
            # wfs layers have the ws prefix, even when adressed from a workspace service url
            if ":" in layer:
                layer = ws + ":" + layer.split(":")[1]
            else:
                layer = ws + ":" + layer
    #            get_logger("CheckMapstore").debug(f"found workspace '{ws}' in url '{ourl}', setting url to '{url}' and layer to '{layer}'")

    return (url, layer)
