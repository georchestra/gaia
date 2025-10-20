#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import current_app as app
from geordash.logwrap import get_logger
from lxml import etree
import psutil
import os


def getelemat(xml: etree._ElementTree, path: str, nsmap=None):
    r = xml.xpath(path, namespaces=nsmap)
    if len(r) > 0:
        return r[0].text
    return None


def getelemsat(xml: etree._ElementTree, path: str, nsmap=None) -> list:
    r = xml.xpath(path, namespaces=nsmap)
    if len(r) > 0:
        ret = list()
        for e in r:
            ret.append(e.text)
        return ret
    return None


def find_tomcat_geoserver_catalina_base():
    """try hard to find the path of the geoserver's tomcat catalina base
    iterate of the list of processes, and try to find one which has:
    - java for the process name
    - catalina.base in its args
    when found, read the l/p for each jdbc resource
    """
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=["name", "cmdline", "environ"])
            if pinfo["name"] == "java" and "/geoserver" in " ".join(pinfo["cmdline"]):
                for a in pinfo["cmdline"]:
                    if "-Dcatalina.base=" in a:
                        return a.split("=")[1]
                if (
                    pinfo["environ"] != None
                    and type(pinfo["environ"]) == dict
                    and "CATALINA_BASE" in pinfo["environ"]
                ):
                    return pinfo["environ"]["CATALINA_BASE"]
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None


def find_tomcat_geoserver_jdbc_resources():
    catalinabase = find_tomcat_geoserver_catalina_base()
    if catalinabase is None:
        path = "/srv/tomcat/geoserver/conf/server.xml"
    else:
        path = f"{catalinabase}/conf/server.xml"
    # check for file existence, without checking if we can actually read it
    if not os.access(path, os.F_OK):
        get_logger("Utils").error(
            f"{path} not found, dunno where to look for jdbc resources"
        )
        return None
    try:
        fp = open(path)
    except PermissionError:
        get_logger("Utils").error(f"cant read {path}, not the right group/modes ?")
        return None
    else:
        get_logger("Utils").info(f"parsing {path} to find JNDI resources")
        ret = dict()
        with fp:
            xml = etree.parse(fp)
            r = xml.xpath(
                "/Server/GlobalNamingResources/Resource[@type='javax.sql.DataSource' and @driverClassName='org.postgresql.Driver']"
            )
            if len(r) > 0:
                for e in r:
                    # parses jdbc:postgresql://host:port/database?properties
                    url = e.get("url")
                    parts = url.split("/")
                    if ":" in parts[2]:
                        p = parts[2].split(":")
                        host = p[0]
                        port = p[1]
                    else:
                        host = parts[2]
                        port = 5432
                    ret[e.get("name")] = {
                        "username": e.get("username"),
                        "password": e.get("password"),
                        "database": parts[3].split("?")[0],
                        "host": host,
                        "port": port,
                    }
        return ret


def find_geoserver_datadir(default):
    """try hard to find the path of the geoserver datadir
    iterate of the list of processes, and try to find one which has:
    - java for the process name
    - either:
      - -DGEOSERVER_DATA_DIR in its commandline
      - or GEOSERVER_DATA_DIR in its environment
    if not found and the fallback path given was None, return the default value for ansible deployments
    """
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=["name", "cmdline", "environ"])
            if pinfo["name"] == "java":
                for a in pinfo["cmdline"]:
                    if "-DGEOSERVER_DATA_DIR=" in a:
                        return a.split("=")[1]
                if (
                    pinfo["environ"] != None
                    and type(pinfo["environ"]) == dict
                    and "GEOSERVER_DATA_DIR" in pinfo["environ"]
                ):
                    return pinfo["environ"]["GEOSERVER_DATA_DIR"]
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if os.getenv('GEOSERVER_DATA_DIR'):
        default = os.getenv('GEOSERVER_DATA_DIR')

    if default is None:
        default = "/srv/data/geoserver"
    path = f"{default}/global.xml"
    if not os.access(path, os.F_OK):
        get_logger("Utils").error(
            f"{path} not found, dunno where to find geoserver datadir"
        )
        return None
    try:
        fp = open(path)
    except PermissionError:
        get_logger("Utils").error(f"cant read {path}, not the right group/modes ?")
        return None
    return default


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
