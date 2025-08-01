#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery import shared_task
from celery import group
from flask import current_app as app
from osgeo.ogr import Open

from gsdscanner import GSDatadirScanner
from gsdscanner.datastore import Datastore
from gsdscanner.featuretype import FeatureType
from gsdscanner.coveragestore import Coveragestore
from gsdscanner.coverage import Coverage
from gsdscanner.layer import Layer
from gsdscanner.style import Style
from gsdscanner.sld import SLD
from gsdscanner.vectordata import VectorData
from gsdscanner.rasterdata import RasterData
from gsdscanner.workspace import Workspace

from geordash.logwrap import get_logger

import os
import re


@shared_task()
def gsdatadir(defpath=None):
    gsd = app.extensions["owscache"].get_geoserver_datadir_view(
        defpath=defpath, parse_now=True
    )
    if gsd is None:
        return False
    taskslist = list()
    for colltype in gsd.available_keys:
        if colltype == "namespaces":
            continue
        for k in gsd.collections[colltype].coll:
            taskslist.append(gsdatadir_item.s(colltype, k, defpath))
    grouptask = group(taskslist)
    groupresult = grouptask.apply_async()
    groupresult.save()
    return groupresult


@shared_task()
def gsdatadir_item(colltype, key, defpath=None, gsd=None):
    if gsd is None:
        gsd = app.extensions["owscache"].get_geoserver_datadir_view(
            defpath=defpath, parse_now=True
        )
    if gsd is None:
        return False
    if colltype not in gsd.available_keys:
        return False
    item = gsd.collections[colltype].coll.get(key)
    if item is None:
        return False
    ret = dict()
    ret["problems"] = list()
    match colltype:
        case "datastores":
            return check_datastore(gsd, item, key, ret)
        case "coveragestores":
            return check_coveragestore(gsd, item, key, ret)
        case "featuretypes":
            return check_featuretype(gsd, item, key, ret)
        case "coverages":
            return check_coverage(gsd, item, key, ret)
        case "layers":
            return check_layer(gsd, item, key, ret)
        case "styles":
            return check_style(gsd, item, key, ret)
        case "slds":
            return check_sld(gsd, item, key, ret)
        case "rasterdatas":
            return check_rasterdata(gsd, item, key, ret)
        case "vectordatas":
            return check_vectordata(gsd, item, key, ret)
        case "workspaces":
            return check_workspace(gsd, item, key, ret)
        case _:
            # we dont test namespaces, what's the point
            pass
    return ret


def check_datastore(gsd: GSDatadirScanner, item: Datastore, key: str, ret: dict):
    if not gsd.collections["workspaces"].has(item.workspaceid):
        ret["problems"].append(
            {
                "type": "NoSuchWorkspace",
                "wsid": item.workspaceid,
                "stype": "datastore",
                "skey": key,
            }
        )
    if item.type in [
        "Shapefile",
        "Directory of spatial files (shapefiles)",
        "GeoPackage",
    ]:
        if item.connurl is None:
            ret["problems"].append({"type": "EmptyConnUrl", "skey": key})
        else:
            if item.type == "GeoPackage":
                if not os.path.isfile(item.connurl):
                    ret["problems"].append(
                        {"type": "NoSuchFile", "path": item.connurl, "skey": key}
                    )
                # check for existence in vectordata collection
                vdk = item.connurl.replace("/", "~")
                if not gsd.collections["vectordatas"].has(vdk):
                    ret["problems"].append(
                        {"type": "NoSuchVectorData", "vdk": vdk, "skey": key}
                    )
                else:
                    vd = gsd.collections["vectordatas"].coll.get(vdk)
                    vd.referenced_by.add(key)
            # shapefile and directory of shapefile point at a dir
            else:
                if not os.path.isdir(item.connurl):
                    ret["problems"].append(
                        {"type": "NoSuchDir", "path": item.connurl, "skey": key}
                    )
    elif item.type == "PostGIS (JNDI)":
        # check that the given schema exists
        if not item.tables:
            ret["problems"].append(
                {"type": "NoSuchSchema", "schema": item.schema, "skey": key}
            )
    return ret


def check_coveragestore(
    gsd: GSDatadirScanner, item: Coveragestore, key: str, ret: dict
):
    if not gsd.collections["workspaces"].has(item.workspaceid):
        ret["problems"].append(
            {
                "type": "NoSuchWorkspace",
                "wsid": item.workspaceid,
                "stype": "coveragestore",
                "skey": key,
            }
        )
    if item.type in ["GeoTIFF", "ImageMosaic"]:
        if item.type == "GeoTIFF":
            if not os.path.isfile(item.url):
                ret["problems"].append(
                    {"type": "NoSuchFile", "path": item.url, "skey": key}
                )
            # check for existence in rasterdata collection
            rdk = item.url.replace("/", "~")
            if not gsd.collections["rasterdatas"].has(rdk):
                ret["problems"].append(
                    {"type": "NoSuchRasterData", "rdk": rdk, "skey": key}
                )
            else:
                gsd.collections["rasterdatas"].coll.get(rdk).referenced_by.add(key)
        elif item.type == "ImageMosaic":
            if not os.path.isdir(item.url):
                ret["problems"].append(
                    {"type": "NoSuchDir", "path": item.url, "skey": key}
                )
    return ret


def check_featuretype(gsd: GSDatadirScanner, item: FeatureType, key: str, ret: dict):
    if not gsd.collections["datastores"].has(item.datastoreid):
        ret["problems"].append(
            {"type": "NoSuchDatastore", "dsid": item.datastoreid, "skey": key}
        )
    else:
        ds = gsd.collections["datastores"].coll.get(item.datastoreid)
        if ds.type in [
            "Shapefile",
            "Directory of spatial files (shapefiles)",
            "GeoPackage",
        ]:
            fpath = ds.connurl
            if "shapefile" in ds.type.lower():
                if fpath.endswith("/"):
                    fpath = fpath.removesuffix("/")
                fpath = f"{fpath}/{item.nativename}.shp"
            vdk = fpath.replace("/", "~")
            if gsd.collections["vectordatas"].has(vdk):
                vd = gsd.collections["vectordatas"].coll.get(vdk)
                vd.referenced_by.add(key)
                # check that a layer named from item.nativename exists in the vd matching the gs
                if item.nativename not in vd.layers:
                    ret["problems"].append(
                        {
                            "type": "NoSuchLayer",
                            "stype": ds.type,
                            "lname": item.nativename,
                            "url": vdk,
                        }
                    )
                else:
                    get_logger("CheckGsd").debug(
                        f"{item.nativename} exists in {ds.type} at {ds.connurl} (vdk={vdk}, vd.type={vd.type})"
                    )
            else:
                ret["problems"].append(
                    {"type": "NoSuchVectorData", "vdk": vdk, "skey": ds.id}
                )
        # if datastore is of type JNDI, look for a table name matching nativeName in the linked postgis JNDI cnx
        elif ds.type == "PostGIS (JNDI)":
            if ds.tables and item.nativename not in ds.tables:
                ret["problems"].append(
                    {
                        "type": "NoSuchTableInSchema",
                        "schema": ds.schema,
                        "table": item.nativename,
                        "skey": key,
                    }
                )
    if not gsd.collections["namespaces"].has(item.namespaceid):
        ret["problems"].append(
            {
                "type": "NoSuchNamespace",
                "nsid": item.namespaceid,
                "stype": "featuretype",
                "skey": key,
            }
        )
    return ret


def check_layer(gsd: GSDatadirScanner, item: Layer, key: str, ret: dict):
    """check for:
    - featureType existing (if vector)
    - coverage existing (if raster)
    - default style existing
    - each of the alternative styles existing
    """
    if item.featuretypeid:
        if not gsd.collections["featuretypes"].has(item.featuretypeid):
            ret["problems"].append(
                {"type": "NoSuchFeatureType", "ftid": item.featuretypeid, "skey": key}
            )
    elif item.coverageid:
        if not gsd.collections["coverages"].has(item.coverageid):
            ret["problems"].append(
                {"type": "NoSuchCoverage", "cid": item.coverageid, "skey": key}
            )
    if item.defaultstyleid is not None:
        if not gsd.collections["styles"].has(item.defaultstyleid):
            ret["problems"].append(
                {"type": "NoSuchStyle", "sid": item.defaultstyleid, "skey": key}
            )
    else:
        ret["problems"].append({"type": "LayerHasNoDefaultStyle", "skey": key})
    if item.styleids is not None:
        for sid in item.styleids:
            if not gsd.collections["styles"].has(sid):
                ret["problems"].append({"type": "NoSuchStyle", "sid": sid, "skey": key})
    return ret


def check_coverage(gsd: GSDatadirScanner, item: Coverage, key: str, ret: dict):
    if not gsd.collections["coveragestores"].has(item.coveragestoreid):
        ret["problems"].append(
            {"type": "NoSuchCoveragestore", "dsid": item.coveragestoreid, "skey": key}
        )
    else:
        cs = gsd.collections["coveragestores"].coll.get(item.coveragestoreid)
        if cs.type == "GeoTIFF":
            rdk = cs.url.replace("/", "~")
            if not gsd.collections["rasterdatas"].has(rdk):
                ret["problems"].append(
                    {"type": "NoSuchRasterData", "rdk": rdk, "skey": cs.key}
                )
            else:
                gsd.collections["rasterdatas"].coll.get(rdk).referenced_by.add(key)
        elif cs.type == "ImageMosaic":
            if os.path.isdir(cs.url):
                idx = cs.url
                if idx.endswith("/"):
                    idx = idx.removesuffix("/")
                idx = f"{idx}/{item.nativecoveragename}.shp"
                # check that a shp exists with the same name
                if os.path.isfile(idx):
                    vdk = idx.replace("/", "~")
                    # check that it's in vd
                    if gsd.collections["vectordatas"].has(vdk):
                        vd = gsd.collections["vectordatas"].coll.get(vdk)
                        vd.referenced_by.add(key)
                        if item.nativecoveragename not in vd.layers:
                            ret["problems"].append(
                                {
                                    "type": "NoSuchLayer",
                                    "stype": cs.type,
                                    "url": vdk,
                                    "lname": item.nativecoveragename,
                                }
                            )
                        else:
                            if vd.layers[item.nativecoveragename]["fields"] != [
                                "location"
                            ]:
                                ret["problems"].append(
                                    {"type": "NotTileindex", "vdk": vdk}
                                )
                            else:
                                # iterate over features, check that each of them is an existing rd
                                ds = Open(vd.file)
                                l = ds.GetLayerByName(item.nativecoveragename)
                                for f in l:
                                    rpath = f.GetField("location")
                                    # if not absolute path, prepend the coveragestore url
                                    if not rpath.startswith("/"):
                                        csdir = cs.url
                                        if csdir.endswith("/"):
                                            csdir = csdir.removesuffix("/")
                                        rpath = f"{csdir}/{rpath}"
                                    if os.path.isfile(rpath):
                                        rdk = rpath.replace("/", "~")
                                        # check that it's an existing rd
                                        rd = gsd.collections["rasterdatas"].coll.get(
                                            rdk
                                        )
                                        if rd is not None:
                                            rd.referenced_by.add(key)
                                        else:
                                            ret["problems"].append(
                                                {
                                                    "type": "NoSuchRasterData",
                                                    "rdk": rdk,
                                                    "skey": cs.key,
                                                }
                                            )
                                    else:
                                        ret["problems"].append(
                                            {
                                                "type": "NoSuchFile",
                                                "path": rpath,
                                                "skey": cs.key,
                                            }
                                        )
                                # release gdal resources
                                ds = None
                    else:
                        ret["problems"].append(
                            {"type": "NoSuchVectorData", "vdk": vdk, "skey": cs.id}
                        )
                else:
                    ret["problems"].append(
                        {"type": "NoSuchFile", "path": idx, "skey": cs.key}
                    )

    if not gsd.collections["namespaces"].has(item.namespaceid):
        ret["problems"].append(
            {
                "type": "NoSuchNamespace",
                "nsid": item.namespaceid,
                "stype": "featuretype",
                "skey": key,
            }
        )
    return ret


def check_style(gsd: GSDatadirScanner, item: Style, key: str, ret: dict):
    if "/workspaces/" in item.file:
        if not gsd.collections["workspaces"].has(item.workspaceid):
            ret["problems"].append(
                {
                    "type": "NoSuchWorkspace",
                    "wsid": item.workspaceid,
                    "stype": "style",
                    "skey": key,
                }
            )
    else:
        if item.workspaceid != None:
            # style in global ws shouldnt reference a ws ?
            ret["problems"].append({"type": "StyleInGlobalWorkspace", "skey": key})

    # todo: css styles
    if item.format == "sld":
        sldpath = f"{os.path.dirname(item.file)}/{item.sldfilename}"
        if os.path.isfile(sldpath):
            sk = sldpath.replace("/", "~")
            s = gsd.collections["slds"].coll.get(sk)
            if s is not None:
                s.referenced_by.add(key)
            else:
                ret["problems"].append({"type": "NoSuchSLD", "path": sk, "skey": key})
        else:
            ret["problems"].append({"type": "NoSuchSLD", "path": sldpath, "skey": key})
    return ret


def check_sld(gsd: GSDatadirScanner, item: SLD, key: str, ret: dict):
    if item.filesize <= 0:
        ret["problems"].append({"type": "EmptySLD", "skey": key})
    # styles matching "^tmp[0-9a-f\-]{36}.sld" were generated by mapstore and pushed as-is
    if (
        len(item.referenced_by) == 0
        and re.match("^tmp[0-9a-f\-]{36}.sld", os.path.basename(item.file)) is None
    ):
        ret["problems"].append({"type": "UnusedSLD", "skey": key})
    return ret


def check_rasterdata(gsd: GSDatadirScanner, item: RasterData, key: str, ret: dict):
    """check that rasterdata is referenced/used"""
    if len(item.referenced_by) == 0:
        ret["problems"].append({"type": "UnusedRasterData", "skey": key})
    return ret


def check_vectordata(gsd: GSDatadirScanner, item: VectorData, key: str, ret: dict):
    """check that vectordata is referenced/used"""
    if len(item.referenced_by) == 0:
        ret["problems"].append({"type": "UnusedVectorData", "skey": key})
    return ret


def check_workspace(gsd: GSDatadirScanner, item: Workspace, key: str, ret: dict):
    """check that workspace is referenced (eg not an empty workspace..)"""
    if len(item.referenced_by) == 0:
        ret["problems"].append({"type": "EmptyWorkspace", "skey": key})
    return ret
