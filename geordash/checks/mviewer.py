#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import requests

from flask import current_app as app
from celery import shared_task
from celery import Task
from celery import group
from geordash.logwrap import get_logger
from geordash.mviewer import parse_map
from geordash.utils import unmunge, objtype


@shared_task
def check_all():
    mviewer_configs = app.extensions["owscache"].get_mviewer_configs()
    if not mviewer_configs:
        get_logger("CheckMviewer").info(f"No mviewer configs to check ?")
        return False
    taskslist = list()
    for url in mviewer_configs:
        taskslist.append(check_mviewer.s(url))
    grouptask = group(taskslist)
    groupresult = grouptask.apply_async()
    groupresult.save()
    return groupresult


@shared_task()
def check_mviewer(url):
    r = requests.get(url)
    if r.status_code != 200:
        return {
            "problems": [{"type": "NoSuchResource", "restype": "mviewer", "resid": url}]
        }

    get_logger("CheckMviewer").info(f"Checking mviewer avec url {url}")
    details = parse_map(r.text)
    ret = dict()
    ret["problems"] = list()
    for l in details["layers"] + details["baselayers"]:
        match l["type"]:
            case "wms" | "wfs" | "wmts":
                get_logger("CheckMviewer").info(
                    "uses {} layer name {} from {}".format(
                        l["type"], l["name"], l["url"]
                    )
                )
                s = app.extensions["owscache"].get(l["type"], l["url"])
                if s.s is None:
                    ret["problems"].append(
                        {
                            "type": "OGCException",
                            "url": l["url"],
                            "stype": l["type"],
                            "exception": objtype(s.exception),
                            "exceptionstr": str(s.exception),
                        }
                    )
                else:
                    get_logger("CheckMviewer").debug(
                        "checking for layer presence in ows entry with ts {}".format(
                            s.timestamp
                        )
                    )
                    if l["name"] not in s.contents():
                        ret["problems"].append(
                            {
                                "type": "NoSuchLayer",
                                "url": l["url"],
                                "stype": l["type"],
                                "lname": l["name"],
                            }
                        )
                    if "styles" in l:
                        for s in l["styles"]:
                            r = requests.head(s, allow_redirects=True)
                            if r.status_code != 200:
                                ret["problems"].append({"type": "NoSuchSld", "url": s})
                            else:
                                pass
                                # check that r.text is parsable sld ?
                    if l["templateurl"]:
                        r = requests.head(l["templateurl"], allow_redirects=True)
                        if r.status_code != 200:
                            ret["problems"].append(
                                {
                                    "type": "NoSuchResource",
                                    "restype": "template",
                                    "resid": l["templateurl"],
                                }
                            )
            case _:
                get_logger("CheckMviewer").debug(l)
    return ret
