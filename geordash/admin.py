#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import (
    request,
    render_template,
    url_for,
    make_response,
    jsonify,
    abort,
    redirect,
)
from flask import current_app as app
from geordash.api import geonetwork_subportals, get_res_details, geoserver_workspaces
from geordash.checks.mapstore import get_all_res
from geordash.decorators import is_superuser, check_role
from geordash.utils import unmunge

admin_bp = Blueprint(
    "admin", __name__, url_prefix="/admin", template_folder="templates"
)


@admin_bp.route("/mapstore/configs")
@check_role(role="MAPSTORE_ADMIN")
def mapstore_configs() -> str:
    all_jobs_for_msconfigs = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.mapstore.check_configs", []
    )
    return render_template(
        "admin/mapstore/configs.html", previous_configs_jobs=all_jobs_for_msconfigs
    )


@admin_bp.route("/geonetwork")
@check_role(role="GN_ADMIN")
def geonetwork():
    localgn = app.extensions["conf"].get("localgn", "urls")
    portals = geonetwork_subportals()
    if type(portals) != list:
        return make_response(
            jsonify(
                {"error": f"an error occured when fetching subportals: got {portals}"},
                404,
            )
        )
    for p in portals:
        p["url"] = "/" + localgn + "/" + p["uuid"] + "/fre/csw"
        p["xurl"] = url_for("dashboard.csw", portal=p["uuid"])
    return render_template("admin/geonetwork.html", portals=portals)


@admin_bp.route("/geoserver")
@check_role(role="ADMINISTRATOR")
def geoserver():
    localgs = app.extensions["conf"].get("localgs", "urls")
    ws = geoserver_workspaces()
    if (
        "workspaces" not in ws
        and "workspace" not in ws["workspaces"]
        or type(ws["workspaces"]["workspace"]) != list
    ):
        return make_response(
            jsonify(
                {"error": f"an error occured when fetching workspaces: got {ws}"}, 404
            )
        )
    workspaces = ws["workspaces"]["workspace"]
    return render_template("admin/geoserver.html", workspaces=workspaces)


@admin_bp.route("/mapstore/maps")
@check_role(role="MAPSTORE_ADMIN")
def mapstore_maps():
    maps = get_all_res("MAP")
    res = list()
    for m in maps:
        d = get_res_details(request, m)
        if len(d["groups"]) > 0:
            acls = "<ul>"
            for k, v in d["groups"].items():
                acls += (
                    f"<li>{k}: lecture:{v['canread']}, écriture: {v['canwrite']}</li>"
                )
            acls += "</ul>"
        else:
            acls = "Aucune ACL ? la carte sera visible uniquement par son auteur"
        res.append(
            {
                "url": m.id,
                "title": m.name,
                "owner": d["owner"],
                "acl": acls,
                "xurl": url_for("dashboard.map", mapid=m.id),
                "viewurl": f'<a class="fa" href="/mapstore/#/viewer/{m.id}">view map {m.id}</a>',
            }
        )
    all_jobs_for_ms_maps = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.mapstore.check_resources", ["MAP"]
    )
    return render_template(
        "admin/mapstore/maps.html",
        previous_resources_jobs=all_jobs_for_ms_maps,
        res=res,
    )


@admin_bp.route("/mapstore/contexts")
@check_role(role="MAPSTORE_ADMIN")
def mapstore_contexts():
    contexts = get_all_res("CONTEXT")
    res = list()
    for c in contexts:
        d = get_res_details(request, c)
        if len(d["groups"]) > 0:
            acls = "<ul>"
            for k, v in d["groups"].items():
                acls += (
                    f"<li>{k}: lecture:{v['canread']}, écriture: {v['canwrite']}</li>"
                )
            acls += "</ul>"
        else:
            acls = "Aucune ACL ? le contexte sera visible uniquement par son auteur"
        res.append(
            {
                "url": c.id,
                "title": c.name,
                "owner": d["owner"],
                "acl": acls,
                "xurl": url_for("dashboard.ctx", ctxid=c.id),
                "viewurl": f'<a class="fa" href="/mapstore/#/context/{c.name}">view context {c.name}</a>',
            }
        )
    all_jobs_for_ms_ctxs = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.mapstore.check_resources", ["CONTEXT"]
    )
    return render_template(
        "admin/mapstore/contexts.html",
        previous_resources_jobs=all_jobs_for_ms_ctxs,
        res=res,
    )


@admin_bp.route("/mviewer/forgetconfig/<string:url>")
@check_role(role="SUPERUSER")
def mviewer_forgetconfig(url: str):
    """url: munged url"""
    mviewer_configs = app.extensions["owscache"].get_mviewer_configs()
    if not mviewer_configs:
        return abort(404)
    url = unmunge(url, False)
    if url not in mviewer_configs:
        return abort(404)
    mviewer_configs.remove(url)
    app.extensions["owscache"].set_mviewer_configs(mviewer_configs)
    # XX flash something to the user ?
    return redirect(url_for("dashboard.admin.mviewer_configs"))


@admin_bp.route("/mviewer/configs")
@check_role(role="USER")
def mviewer_configs():
    mviewer_configs = app.extensions["owscache"].get_mviewer_configs()
    if mviewer_configs is None:
        return abort(404)
    confs = list()
    for c in mviewer_configs:
        murl = c.replace("/", "~")
        confs.append(
            {
                "url": c,
                "xurl": url_for("dashboard.mviewer", url=murl),
                "forgeturl": f'<a class="fa" href="{ url_for("dashboard.admin.mviewer_forgetconfig", url=murl) }"><i class="bi bi-trash"></i></a>',
                "viewurl": f'<a class="fa" href="https://geobretagne.fr/mviewer/?config={ c }">view map in mviewer</a>',
            }
        )
    all_jobs_for_mv_configs = app.extensions["rcli"].get_taskids_by_taskname_and_args(
        "geordash.checks.mviewer.check_all", []
    )
    return render_template(
        "admin/mviewer/configs.html",
        previous_resources_jobs=all_jobs_for_mv_configs,
        confs=confs,
    )
