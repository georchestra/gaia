#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery import shared_task
from celery import group
from flask import current_app as app

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


@shared_task()
def gsdatadir(defpath=None):
    gsd = app.extensions["owscache"].get_geoserver_datadir_view(defpath)
    if gsd is None:
        return False
    taskslist = list()
    for colltype in gsd.available_keys:
        for k in gsd.collections[colltype].coll:
            taskslist.append(gsdatadir_item.s(colltype, k, defpath))
    grouptask = group(taskslist)
    groupresult = grouptask.apply_async()
    groupresult.save()
    return groupresult


@shared_task()
def gsdatadir_item(colltype, key, defpath=None):
    gsd = app.extensions["owscache"].get_geoserver_datadir_view(defpath)
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
        case _:
            # we dont test namespaces/workspaces, what's the point
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
    # todo: check vectordata existence
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
    # todo: check rasterdata existence
    return ret


def check_featuretype(gsd: GSDatadirScanner, item: FeatureType, key: str, ret: dict):
    if not gsd.collections["datastores"].has(item.datastoreid):
        ret["problems"].append(
            {"type": "NoSuchDatastore", "dsid": item.datastoreid, "skey": key}
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
    # if datastore is of type JNDI, look for a table name matching nativeName in the linked postgis JNDI cnx
    return ret


def check_layer(gsd: GSDatadirScanner, item: Layer, key: str, ret: dict):
    if item.featuretypeid.startswith("FeatureTypeInfoImpl"):
        if not gsd.collections["featuretypes"].has(item.featuretypeid):
            ret["problems"].append(
                {"type": "NoSuchFeatureType", "ftid": item.featuretypeid, "skey": key}
            )
    elif item.featuretypeid.startswith("CoverageInfoImpl"):
        if not gsd.collections["coverages"].has(item.featuretypeid):
            ret["problems"].append(
                {"type": "NoSuchFeatureType", "ftid": item.featuretypeid, "skey": key}
            )
    return ret


def check_coverage(gsd: GSDatadirScanner, item: Coverage, key: str, ret: dict):
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
        if s.workspaceid != None:
            ret["problems"].append({"type": "WorkspaceInGlobalStyle", "skey": key})
    # check that sldfilename relative to style exists XXX doesnt handle css styles yet
    #    sldpath = dirname(s.file) + '/' + s.sldfilename
    #    if not gds.collections['slds'].has(sldpath) and not sldpath.endswith('.css'):
    #        print(f"{sldpath} not found")
    return ret


def check_sld(gsd: GSDatadirScanner, item: SLD, key: str, ret: dict):
    #    if s.filesize <= 0:
    #        print(f"{s.file} is empty")
    return ret


def check_rasterdata(gsd: GSDatadirScanner, item: RasterData, key: str, ret: dict):
    return ret


def check_vectordata(gsd: GSDatadirScanner, item: VectorData, key: str, ret: dict):
    return ret
