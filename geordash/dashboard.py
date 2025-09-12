#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template, abort, url_for
from flask import current_app as app
import requests
from functools import wraps

from geordash.decorators import is_superuser, check_role
from geordash.checks.mapstore import get_resources_using_ows, get_res
from geordash.api import mapstore_get, gninternalid, get_res_details
from geordash.utils import find_localmduuid, unmunge
from geordash.mviewer import parse_map

import json

# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 1

dash_bp = Blueprint(
    "dashboard", __name__, url_prefix="/gaia", template_folder="templates/dashboard"
)

def debug_only(f):
    @wraps(f)
    def wrapped(**kwargs):
        if not app.debug:
            abort(404)
        return f(**kwargs)
    return wrapped

def get_rescontent_from_resid(restype, resid):
    r = mapstore_get(request, f"rest/geostore/data/{resid}", False)
    res = dict()
    if r.status_code == 200:
        msmap = json.loads(r.content)
        if restype == "MAP":
            llist = msmap["map"]["layers"]
            catlist = msmap["catalogServices"]["services"]
        else:
            if "map" not in msmap["mapConfig"]:
                return dict()
            llist = msmap["mapConfig"]["map"]["layers"]
            catlist = msmap["mapConfig"]["catalogServices"]["services"]
        layers = dict()
        for l in llist:
            if "group" not in l or ("group" in l and l["group"] != "background"):
                if l["type"] in ("wms", "wfs", "wmts"):
                    layers[l["id"]] = l
        res["layers"] = layers
        res["catlist"] = list()
        for k, c in catlist.items():
            e = {
                "key": k,
                "title": c["title"],
                "type": c["type"],
                "url": c["url"],
                "xurl": url_for(
                    "dashboard.ows", stype=c["type"], url=c["url"].replace("/", "~")
                ),
            }
            res["catlist"].append(e)
    else:
        app.logger.error(
            f"failed getting resource {resid} from geostore, got code {r.status_code}, backend said {r.text}"
        )
        return r
    return res


@dash_bp.route("/")
def home():
    return render_template("home.html")

@dash_bp.route("/debug")
@debug_only
def debug():

    return app.extensions["conf"].tostr()

@dash_bp.route("/my-metadata")
@check_role(role="GN_EDITOR")
def my_metadata():
    return render_template("my-metadata.html")


@dash_bp.route("/my-maps-and-apps")
def my_maps_and_apps():
    return render_template("my-maps-and-apps.html")


@dash_bp.route("/csw/<string:portal>")
def csw(portal):
    # XXX for now only support the local GN
    localgn = app.extensions["conf"].get("localgn", "urls")
    cswurl = "/" + localgn + "/" + portal + "/fre/csw"
    service = app.extensions["owscache"].get("csw", cswurl)
    if service.s is None:
        return abort(404)
    cswrecords = list()
    if service.nelems() > 0:
        for uuid, record in service.contents().items():
            cswrecords.append(
                {
                    "title": record.title,
                    "url": record.identifier,
                    "xurl": url_for("dashboard.cswentry", portal=portal, uuid=uuid),
                }
            )
    all_jobs_for_csw = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.csw.check_catalog", [cswurl]
    )
    return render_template(
        "csw.html",
        s=service,
        portal=portal,
        cswrecords=cswrecords,
        url=cswurl.replace("/", "~"),
        previous_jobs=all_jobs_for_csw,
    )


@dash_bp.route("/csw/<string:portal>/<string:uuid>")
def cswentry(portal, uuid):
    # XXX for now only support the local GN
    localgn = app.extensions["conf"].get("localgn", "urls")
    cswurl = "/" + localgn + "/" + portal + "/fre/csw"
    service = app.extensions["owscache"].get("csw", cswurl)
    if service.s is None:
        return abort(404)
    if uuid not in service.contents():
        return abort(404)
    owslinks = list()
    r = service.contents()[uuid]
    gnid = gninternalid(request, uuid)
    for u in r.uris:
        if u["protocol"] in ("OGC:WMS", "OGC:WFS"):
            stype = u["protocol"].split(":")[1].lower()
            if u["url"] is None:
                continue
            url = u["url"].rstrip("?")
            localdomain = "https://" + app.extensions["conf"].get("domainName")
            if url.startswith(localdomain):
                url = url.removeprefix(localdomain)
            owslinks.append(
                {
                    "type": stype,
                    "url": url,
                    "layername": u["name"],
                    "descr": u["description"],
                }
            )
    all_jobs_for_cswrecord = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.csw.check_record", [cswurl, uuid]
    )
    return render_template(
        "cswentry.html",
        localgn=localgn,
        s=service,
        portal=portal,
        url=cswurl.replace("/", "~"),
        r=r,
        gnid=gnid,
        owslinks=owslinks,
        previous_jobs=all_jobs_for_cswrecord,
    )


@dash_bp.route("/ows/<string:stype>/<string:url>")
def ows(stype, url):
    if stype not in ("wms", "wmts", "wfs"):
        return abort(412)
    murl = url
    url = unmunge(url)
    service = app.extensions["owscache"].get(stype, url)
    if service.s is None:
        return abort(404)
    used_by = get_resources_using_ows(stype, url)
    layers = list()
    for lname, l in service.contents().items():
        layers.append(
            {
                "title": l.title,
                "url": lname,
                "xurl": url_for(
                    "dashboard.owslayer", stype=stype, url=murl, lname=lname
                ),
            }
        )
    all_jobs_for_ows = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.ows.owsservice", [stype, url]
    )
    return render_template(
        "ows.html",
        s=service,
        layers=layers,
        type=stype,
        url=url.replace("/", "~"),
        consumers=used_by,
        previous_jobs=all_jobs_for_ows,
    )


@dash_bp.route("/ows/<string:stype>/<string:url>/<string:lname>")
def owslayer(stype, url, lname):
    if stype not in ("wms", "wmts", "wfs"):
        return abort(412)
    url = unmunge(url)
    service = app.extensions["owscache"].get(stype, url)
    if service.s is None:
        return abort(404)
    # if a wfs from geoserver, prepend ws to lname
    if (
        stype == "wfs"
        and ":" not in lname
        and service.s.updateSequence
        and service.s.updateSequence.isdigit()
    ):
        ws = url.split("/")[-2]
        lname = f"{ws}:{lname}"
    if lname not in service.contents():
        return abort(404)
    localmduuids = find_localmduuid(service.s, lname)
    params = ""
    if not url.startswith("http") and stype == "wms":
        bbox = service.contents()[lname].boundingBox
        params = "service=WMS&version=1.1.1&request=GetMap&styles=&format=application/openlayers&"
        params += f"srs={bbox[4]}&layers={lname}&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}&height=576&width=768"
    used_by = get_resources_using_ows(stype, url, lname)
    all_jobs_for_owslayer = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.ows.owslayer", [stype, url, lname]
    )
    return render_template(
        "owslayer.html",
        s=service,
        type=stype,
        url=url.replace("/", "~"),
        lname=lname,
        consumers=used_by,
        previewqparams=params,
        localmduuids=localmduuids,
        previous_jobs=all_jobs_for_owslayer,
    )


@dash_bp.route("/mviewer/<string:url>")
def mviewer(url):
    url = unmunge(url, False)
    r = requests.get(url)
    if r.status_code == 200:
        if r.headers["content-type"] == "text/xml":
            r.encoding = "utf-8"
        mviewer_configs = app.extensions["owscache"].get_mviewer_configs()
        if not mviewer_configs:
            app.extensions["owscache"].set_mviewer_configs(
                set(
                    {
                        url,
                    }
                )
            )
        else:
            if url not in mviewer_configs:
                mviewer_configs.add(url)
                app.extensions["owscache"].set_mviewer_configs(mviewer_configs)

        all_jobs_for_mviewer = app.extensions["rcli"].get_taskids_by_taskname_and_args(
            "geordash.checks.mviewer.check_mviewer", [url]
        )
        return render_template(
            "mviewer.html",
            url=url.replace("/", "~"),
            previous_jobs=all_jobs_for_mviewer,
            details=parse_map(r.text),
        )
    else:
        return abort(404)


@dash_bp.route("/map/<int:mapid>")
def map(mapid):
    m = get_res("MAP", mapid)
    if not m:
        return abort(404)
    all_jobs_for_mapid = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.mapstore.check_res", ["MAP", mapid]
    )
    resc = get_rescontent_from_resid("MAP", mapid)
    if type(resc) != dict:
        return f"failed getting map resource {mapid} from geostore, got code {resc.status_code}, backend said {resc.text}"
    return render_template(
        "map.html",
        mapid=mapid,
        details=get_res_details(request, m),
        resources=resc,
        previous_jobs=all_jobs_for_mapid,
    )


@dash_bp.route("/context/<int:ctxid>")
def ctx(ctxid):
    c = get_res("CONTEXT", ctxid)
    if not c:
        return abort(404)
    all_jobs_for_ctxid = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.mapstore.check_res", ["CONTEXT", ctxid]
    )
    resc = get_rescontent_from_resid("CONTEXT", ctxid)
    if type(resc) != dict:
        return f"failed getting ctx resource {ctxid} from geostore, got code {resc.status_code}, backend said {resc.text}"
    return render_template(
        "ctx.html",
        ctxid=ctxid,
        details=get_res_details(request, c),
        resources=resc,
        previous_jobs=all_jobs_for_ctxid,
    )
