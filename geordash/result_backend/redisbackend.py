#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import redis
import json

try:
    from geordash.logwrap import get_logger
except:
    # to run this module standalone for testing
    import logging

    logging.basicConfig(level=logging.DEBUG)

    def get_logger(name):
        return logging.getLogger(name)


import sys
from datetime import datetime, timezone


class RedisClient:
    def __init__(self, url):
        self.r = redis.Redis.from_url(url)
        self.task_by_taskname = dict()
        # store relationship between 'extra' grouptasks stored as task-meta-*
        # and the ones found in taskset-meta-* to avoid storing (and reporting)
        # them twice. Those 'extra' grouptasks are scheduled by beat, and arent
        # seen when grouptasks are manually triggered.
        self.child_tasksets = dict()
        for k in self.r.scan_iter("celery-task-meta-*"):
            v = self.get(k.decode())
            try:
                task = json.loads(v)
            except json.JSONDecodeError as e:
                get_logger("RedisClient").error(f"discarding {k}, not json ? {e}")
                continue
            if "children" in task and len(task["children"]) > 0:
                tsid = task["result"][0][0]
                self.child_tasksets[tsid] = k.decode()[17:]
                get_logger("RedisClient").debug(f"task {k} has a child taskset: {tsid}")
            name = task["name"]
            args = task["args"]
            date_done = task["date_done"]
            if type(date_done) == str:
                date_done = datetime.fromisoformat(date_done).replace(
                    tzinfo=timezone.utc
                )
            self.add_taskid_for_taskname_and_args(
                name, args, k.decode()[17:], date_done
            )

        # analyse tasksets
        for k in self.r.scan_iter("celery-taskset-meta-*"):
            tsid = k.decode()[20:]
            if tsid in self.child_tasksets:
                get_logger("RedisClient").debug(
                    f"ignoring taskset with id {tsid}, already stored with task {self.child_tasksets[tsid]}"
                )
                continue
            (name, args, date_done) = self.get_taskset_details(k.decode())
            self.add_taskid_for_taskname_and_args(name, args, tsid, date_done)

    def get_taskset_details(self, key):
        """
        from a given taskset, try to reconstruct the grouptask properties
        (eg name, args & date_done) from the child tasks properties
        """
        v = self.get(key)
        if v is None:
            get_logger("RedisClient").error(
                f"found nothing for a taskset with {key}, shouldnt happen"
            )
            return (None, None, None)
        try:
            task = json.loads(v)
        except json.JSONDecodeError as e:
            get_logger("RedisClient").error(f"discarding {key}, not json ? {e}")
        name = None
        args = None
        date_done = None
        for f in task["result"][1]:
            tid = f[0][0]
            tj = self.get(tid)
            if tj is None:
                continue
            try:
                task = json.loads(tj)
            except json.JSONDecodeError as e:
                get_logger("RedisClient").error(f"discarding {tid}, not json ? {e}")
                continue
            if name is None:
                name = task["name"]
            else:
                if task["name"] != name:
                    get_logger("RedisClient").error(
                        f"{name} mismatched task name for {tid}"
                    )
            if args is None:
                args = task["args"][:-1]
            # specialcase for check_resources job checking all maps *and* resources
            if (
                (
                    name.endswith("check_res")
                    or name.endswith("check_mviewer")
                    or name.endswith("gsdatadir_item")
                )
                and args is not None
                and task["args"][:-1] != args
            ):
                args = []
            # find the last finishing job
            if type(task["date_done"]) == str:
                subtask_done = datetime.fromisoformat(task["date_done"]).replace(
                    tzinfo=timezone.utc
                )
            else:
                subtask_done = task["date_done"]
                get_logger("RedisClient").debug(
                    f"sd={subtask_done}, type={type(subtask_done)}"
                )
            if date_done is None:
                date_done = subtask_done
            elif subtask_done is not None and subtask_done > date_done:
                date_done = subtask_done
            # print(f"{tid} {task['name']} {task['args'][:-1]} {task['date_done']} {date_done}")
        if name is not None:
            if name.endswith("owslayer"):
                name = "geordash.checks.ows.owsservice"
            if name.endswith("check_res"):
                name = "geordash.checks.mapstore.check_resources"
            if name.endswith("check_record"):
                name = "geordash.checks.csw.check_catalog"
            if name.endswith("check_mviewer"):
                name = "geordash.checks.mviewer.check_all"
            if name.endswith("gsdatadir_item"):
                name = "geordash.checks.gsd.gsdatadir"
        return (name, args, date_done)

    def get(self, key):
        #        print(f"get({key}) called")
        if key[:17] == "celery-task-meta-" or key[:20] == "celery-taskset-meta-":
            return self.r.get(key)
        else:
            if isinstance(key, str):
                nk = "celery-task-meta-".encode() + key.encode()
            else:
                nk = "celery-task-meta-".encode() + key
            x = self.r.get(nk)
            if x is not None:
                return x
            else:
                if isinstance(key, str):
                    nk = "celery-taskset-meta-".encode() + key.encode()
                else:
                    nk = "celery-taskset-meta-".encode() + key
                return self.r.get(nk)

    def forget(self, taskid):
        get_logger("RedisClient").debug(f"forgetting {taskid}")
        v = self.get(taskid)
        if v is None:
            return None
        task = json.loads(v)
        taskname = None
        args = None
        if "name" in task:
            taskname = task["name"]
            args = task["args"]
        else:
            if len(task["result"][1]) == 0:
                get_logger("RedisClient").error(f"{taskid} has no child tasks ?")
                return None
            # taskset, take name & args from the first task of the set
            ftid = task["result"][1][0][0][0]
            tj = self.get(ftid)
            try:
                task = json.loads(tj)
            except json.JSONDecodeError as e:
                get_logger("RedisClient").error(f"discarding {ftid}, not json ?")
                return None
            except TypeError as e:
                get_logger("RedisClient").error(f"discarding {ftid}, {str(e)}")
                return None
            args = task["args"][:-1]
            if task["name"].endswith("owslayer"):
                taskname = "geordash.checks.ows.owsservice"
            if task["name"].endswith("check_res"):
                taskname = "geordash.checks.mapstore.check_resources"
                args = []
            if task["name"].endswith("check_mviewer"):
                taskname = "geordash.checks.mviewer.check_all"
                args = []
            if task["name"].endswith("gsdatadir_item"):
                taskname = "geordash.checks.gsd.gsdatadir"
                args = []
            if task["name"].endswith("check_record"):
                taskname = "geordash.checks.csw.check_catalog"

        if taskname in self.task_by_taskname:
            if tuple(args) in self.task_by_taskname[taskname]:
                taskids = self.task_by_taskname[taskname][tuple(args)]
                if taskid in taskids:
                    del taskids[taskid]

        # find child tasksets to remove/forget:
        taskids = [key for key, val in self.child_tasksets.items() if val == taskid]
        if taskids:
            return taskids[0]
        return None

    def get_taskids_by_taskname_and_args(self, taskname, args):
        if taskname in self.task_by_taskname:
            if tuple(args) in self.task_by_taskname[taskname]:
                taskids = self.task_by_taskname[taskname][tuple(args)]
                found_taskids = list()
                dropped_taskids = list()
                for taskid in taskids:
                    v = self.get(taskid)
                    if v == None:
                        dropped_taskids.append(taskid)
                        continue
                    # refresh finished ts from backend if not set
                    if taskids[taskid]["finished"] is None:
                        taskb = json.loads(v)
                        date_done = None
                        if "date_done" in taskb and taskb["date_done"] is not None:
                            if type(taskb["date_done"]) == str:
                                date_done = datetime.fromisoformat(
                                    taskb["date_done"]
                                ).replace(tzinfo=timezone.utc)
                            else:
                                date_done = taskb["date_done"]
                        if not "name" in taskb:  # taskset
                            (x, y, date_done) = self.get_taskset_details(
                                "celery-taskset-meta-" + taskid
                            )
                        if date_done is not None:
                            taskids[taskid] = {"finished": date_done}
                    if taskids[taskid]["finished"] is not None:
                        found_taskids.append(
                            {
                                "id": taskid,
                                "finished": taskids[taskid]["finished"].timestamp(),
                            }
                        )

                # remove taskids from the in-memory list
                for t in dropped_taskids:
                    del taskids[t]
                return found_taskids
        return None

    def add_taskid_for_taskname_and_args(self, taskname, args, taskid, finished=None):
        if taskname not in self.task_by_taskname:
            self.task_by_taskname[taskname] = dict()
        if args is None:  # invalid task ?
            return
        if tuple(args) not in self.task_by_taskname[taskname]:
            self.task_by_taskname[taskname][tuple(args)] = dict()
        self.task_by_taskname[taskname][tuple(args)][taskid] = {"finished": finished}

    def get_last_taskid_for_taskname_and_args(self, taskname, args):
        tasks = self.get_taskids_by_taskname_and_args(taskname, args)

        # lambda function for max() call below
        def compare_task_by_finished_ts(o):
            if isinstance(o["finished"], datetime):
                return str(o["finished"])
            return o["finished"]

        if tasks:
            last_task = max(tasks, key=compare_task_by_finished_ts)
            return last_task["id"]
        return None


if __name__ == "__main__":
    import sys

    sys.path.append(".")
    import config

    rc = RedisClient(config.url)
    print(rc.task_by_taskname["geordash.checks.mapstore.check_res"].keys())
    print(rc.task_by_taskname["geordash.checks.mapstore.check_res"][("CONTEXT", 38)])
    print(
        tuple(["CONTEXT", 38])
        in rc.task_by_taskname["geordash.checks.mapstore.check_res"]
    )
    print(len(rc.get("celery-task-meta-c2bd9571-0ff0-4272-b882-f813c35a2d44")))
    print(len(rc.get("c2bd9571-0ff0-4272-b882-f813c35a2d44")))
    print(len(rc.get("celery-taskset-meta-9678631a-7fb6-42e0-83a9-1b9a9558949f")))
    tasks = rc.get_taskids_by_taskname_and_args(
        "geordash.checks.mapstore.check_res", ["MAP", 1]
    )
    print(tasks)
    for f in tasks:
        print(len(rc.get(f["id"])))
        print(f["finished"])
        j = json.loads(rc.get(f["id"]))
        print(j["result"]["problems"])
    print(
        rc.get_taskids_by_taskname_and_args(
            "geordash.checks.ows.owsservice", ["wfs", "/wxs/geor_loc/ows"]
        )
    )
    print(
        rc.get_last_taskid_for_taskname_and_args(
            "geordash.checks.ows.owsservice", ["wfs", "/wxs/geor_loc/ows"]
        )
    )
