#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery.result import AsyncResult, GroupResult
from celery import group
from flask import current_app as app
from flask import Blueprint
from flask import request, abort
from flask import jsonify
import requests

from geordash.utils import unmunge
from geordash.checks.mapstore import check_res, check_configs, check_resources
from geordash.tasks.fetch_csw import get_records
from geordash.tasks.gsdatadir import parse_gsdatadir
import geordash.checks.ows
import geordash.checks.csw
import geordash.checks.mviewer
import geordash.checks.gsd
from geordash.decorators import check_role

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@tasks_bp.get("/result/<id>")
def result(id: str) -> dict[str, object]:
    result = GroupResult.restore(id)
    finished = None
    value = None
    completed = None
    args = None
    name = None
    if result is None:
        result = AsyncResult(id)
        # regular task triggered by beat, the asyncresult first result entry contains the groupresult id
        if type(result.result) == list and result.name in (
            "geordash.checks.mapstore.check_resources",
            "geordash.checks.mviewer.check_all",
            "geordash.checks.ows.owsservice",
            "geordash.checks.csw.check_catalog",
            "geordash.checks.gsd.gsdatadir",
        ):
            #            print(f"real taskset id is {result.result[0][0]}")
            result = GroupResult.restore(result.result[0][0])
            # shouldnt happen, but make sure we have 'a result'...
            if result is None:
                result = AsyncResult(id)
    if type(result) == AsyncResult:
        # date_done is a datetime
        finished = result.date_done
        if result.state == "FAILURE" and isinstance(result.result, Exception):
            s = f"{str(result.result)} {result.traceback}"
            app.logger.error(
                f"task {result.id} badly failed with a {type(result.result)} exception, returning exception string/traceback to the client: {s}"
            )
            return {"taskid": result.id, "ready": True, "successful": False, "value": s}
        else:
            value = result.get() if result.ready() else result.result
    else:
        completed = f"{result.completed_count()} / {len(result.children)}"
        (name, args, finished) = app.extensions["rcli"].get_taskset_details(result.id)
        if result.ready():
            value = list()
            for r in result.results:
                try:
                    value.append({"args": r.args, "problems": r.get()["problems"]})
                except Exception as e:
                    app.logger.error(
                        f"failed getting results from celery on task {r.id} with {r.args}, got {str(e)}"
                    )
    ready = result.ready()
    return {
        "taskid": result.id,
        "ready": ready,
        "completed": completed,
        "task": result.name if hasattr(result, "name") else name,
        "finished": (finished.timestamp() if finished is not None else False),
        "args": result.args if hasattr(result, "args") else args,
        "successful": result.successful() if ready else None,
        "state": result.state if hasattr(result, "state") else None,
        "value": value,
    }


@tasks_bp.get("/lastresultbytask/<string:taskname>")
def last_result_by_taskname_and_args(taskname: str) -> dict[str, object]:
    args = request.args.get("taskargs", None)
    if args:
        argslist = args.split(",")
    else:
        argslist = []
    app.logger.debug(f"last_result_by_taskname_and_args({taskname},{argslist})")
    taskid = app.extensions["rcli"].get_last_taskid_for_taskname_and_args(
        taskname, argslist
    )
    if taskid:
        app.logger.debug(f"fetching result for taskid {taskid}")
        return result(taskid)
    return jsonify("notask")


@tasks_bp.get("/forget/<id>")
@check_role(role="SUPERUSER")
def forget(id: str):
    # forget first in the revmap
    childid = app.extensions["rcli"].forget(id)
    result = GroupResult.restore(id)
    if result is None:
        result = AsyncResult(id)
    else:
        # delete taskset from redis
        result.delete()
    # if is a taskset, should also forget all subtasks
    result.forget()
    if childid:
        app.logger.debug(f"dropping {childid} as linked to {id}")
        childres = GroupResult.restore(childid)
        childres.delete()
        childres.forget()
    return jsonify("ok")


@tasks_bp.get("/forgetogc/<string:stype>/<string:url>")
@check_role(role="SUPERUSER")
def forgetogc(stype, url):
    if stype not in ("wms", "wmts", "wfs", "csw"):
        return abort(412)
    url = unmunge(url)
    n = app.extensions["owscache"].forget(stype, url)
    return {"deleted": n}


@tasks_bp.get("/parsegsd.json")
def start_parse_gsd():
    result = parse_gsdatadir.delay()
    return {"taskid": result.id}


@tasks_bp.get("/fetchcswrecords/<string:portal>.json")
def start_fetch_csw(portal: str):
    result = get_records.delay(portal)
    return {"taskid": result.id}


@tasks_bp.get("/taskresults/<string:taskid>")
def get_task_result(taskid: str):
    """
    taskid should be the task id for a get_records or parse_gsdatadir task
    if given a garbage id, celery returns a None result and state=PENDING ?
    but how should one differentiate that from a really PENDING task ?
    """
    result = AsyncResult(taskid)
    return {
        "state": result.state,
        "completed": result.result,
    }


@tasks_bp.route("/check/mapstore/configs.json")
def check_mapstore_configs():
    result = check_configs.delay()
    return {"result_id": result.id}


@tasks_bp.route("/check/map/<int:mapid>.json")
def check_map(mapid):
    result = check_res.delay("MAP", mapid)
    return {"result_id": result.id}


@tasks_bp.route("/check/context/<int:ctxid>.json")
def check_ctx(ctxid):
    result = check_res.delay("CONTEXT", ctxid)
    return {"result_id": result.id}


@tasks_bp.route("/check/mapstore/maps.json")
def check_mapstore_maps():
    groupresult = check_resources(["MAP"])
    if groupresult.id:
        app.extensions["rcli"].add_taskid_for_taskname_and_args(
            "geordash.checks.mapstore.check_resources", ["MAP"], groupresult.id
        )
    return {"result_id": groupresult.id}


@tasks_bp.route("/check/mapstore/contexts.json")
def check_mapstore_contexts():
    groupresult = check_resources(["CONTEXT"])
    if groupresult.id:
        app.extensions["rcli"].add_taskid_for_taskname_and_args(
            "geordash.checks.mapstore.check_resources", ["CONTEXT"], groupresult.id
        )
    return {"result_id": groupresult.id}


@tasks_bp.route("/check/mapstore/resources.json")
def check_mapstore_resources():
    groupresult = check_resources()
    if groupresult.id:
        app.extensions["rcli"].add_taskid_for_taskname_and_args(
            "geordash.checks.mapstore.check_resources", [], groupresult.id
        )
    return {"result_id": groupresult.id}


@tasks_bp.route("/check/mviewer/configs.json")
def check_all_mviewer():
    groupresult = geordash.checks.mviewer.check_all()
    if groupresult.id:
        app.extensions["rcli"].add_taskid_for_taskname_and_args(
            "geordash.checks.mviewer.check_all", [], groupresult.id
        )
    return {"result_id": groupresult.id}


@tasks_bp.route("/check/mviewer/<string:url>.json")
def check_mviewer(url):
    url = unmunge(url, False)
    r = requests.get(url)
    if r.status_code != 200:
        return abort(404)
    result = geordash.checks.mviewer.check_mviewer.delay(url)
    return {"result_id": result.id}


@tasks_bp.route("/check/geoserver/datadir.json")
def check_geoserver_datadir():
    groupresult = geordash.checks.gsd.gsdatadir()
    if groupresult.id:
        app.extensions["rcli"].add_taskid_for_taskname_and_args(
            "geordash.checks.gsd.gsdatadir", [], groupresult.id
        )
    return {"result_id": groupresult.id}

@tasks_bp.route("/check/geoserver/datadir/<string:colltype>/<string:itemid>.json")
def check_geoserver_datadir_item(colltype, itemid):
    gsd = app.extensions["owscache"].get_geoserver_datadir_view()
    ctype = f"{colltype}s"
    if gsd is None:
        return abort(404)
    if ctype not in gsd.available_keys:
        return abort(404)
    if gsd.collections[ctype].coll.get(itemid) is None:
        return abort(404)
    result = geordash.checks.gsd.gsdatadir_item.delay(ctype, itemid, None)
    return {"result_id": result.id}

@tasks_bp.route("/check/ows/<string:stype>/<string:url>/<string:lname>.json")
def check_owslayer(stype, url, lname):
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
    result = geordash.checks.ows.owslayer.delay(stype, url, lname, True)
    return {"result_id": result.id}


@tasks_bp.route("/check/owsservice/<string:stype>/<string:url>.json")
def check_owsservice(stype, url):
    app.logger.info(
        f"check_owsservice triggered by webui, checking owsservice in {stype} {url}"
    )
    if stype not in ("wms", "wmts", "wfs"):
        return abort(412)
    url = unmunge(url)
    service = app.extensions["owscache"].get(stype, url)
    if service.s is None:
        return abort(404)
    groupresult = geordash.checks.ows.owsservice(stype, url)
    if not groupresult:
        return abort(404)
    if groupresult.id:
        app.logger.debug(f"returning grouptask id {groupresult.id} for owsservice")
        app.extensions["rcli"].add_taskid_for_taskname_and_args(
            "geordash.checks.ows.owsservice", [stype, url], groupresult.id
        )
    return {"result_id": groupresult.id}


@tasks_bp.route("/check/csw/<string:url>/<string:uuid>.json")
def check_cswrecord(url, uuid):
    url = unmunge(url)
    service = app.extensions["owscache"].get("csw", url)
    if service.s is None:
        return abort(404)
    result = geordash.checks.csw.check_record.delay(url, uuid)
    return {"result_id": result.id}


@tasks_bp.route("/check/cswservice/<string:url>.json")
def check_cswservice(url):
    app.logger.info(
        f"check_cswservice triggered by webui, checking cswservice in {url}"
    )
    url = unmunge(url)
    service = app.extensions["owscache"].get("csw", url)
    if service.s is None:
        return abort(404)
    groupresult = geordash.checks.csw.check_catalog(url)
    if not groupresult:
        return abort(404)
    if groupresult.id:
        app.logger.debug(f"returning grouptask id {groupresult.id} for cswservice")
        app.extensions["rcli"].add_taskid_for_taskname_and_args(
            "geordash.checks.csw.check_catalog", [url], groupresult.id
        )
    return {"result_id": groupresult.id}

@tasks_bp.route("/check/gndatadir/result.json")
def check_gndatadir():
    # metalist = geordash.checks.gn_datadir.check_gn_meta()
    # return {"result_id": metalist}
    result = geordash.checks.gn_datadir.check_gn_meta.delay()
    return {"result_id": result.id}
