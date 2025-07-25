#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import current_app as app
from celery import shared_task
from geordash.logwrap import get_logger
from geordash.owscapcache import OwsCapCache

@shared_task(bind=True)
def parse_gsdatadir(self):
    """
    parse xml in the datadir, and analyze spatial datas
    """
    gsd = app.extensions["owscache"].get_geoserver_datadir_view()
    i = 0
    ni = 0
    for t in gsd.available_keys:
        i += 1
        self.update_state(
            state="PROGRESS",
            meta={
                "current": f"({t}) {i}",
                "total": len(gsd.available_keys)
            },
        )
        gsd.parse(t)
        ni += len(gsd.collections[t].coll)
        get_logger("ParseGsDatadir").debug(
            f"current={t} ({len(gsd.collections[t].coll)} entries), done {i}/{len(gsd.available_keys)}"
        )
    gsd.parsed=True
    app.extensions["owscache"].update_geoserver_datadir_view(gsd)
    return ni
