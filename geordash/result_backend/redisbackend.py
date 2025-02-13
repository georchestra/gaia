#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import redis
import json
from geordash.logwrap import get_logger
import sys
from datetime import datetime

class RedisClient:
    def __init__(self, url, app):
        self.r = redis.Redis.from_url(url)
        self.task_by_taskname = dict()
        for k in self.r.scan_iter("celery-task-meta-*"):
            v = self.get(k.decode())
            try:
                task = json.loads(v)
            except json.JSONDecodeError as e:
                get_logger("RedisClient").error(f"discarding {k}, not json ? {e}")
                continue
            name = task["name"]
            args = task["args"]
            self.add_taskid_for_taskname_and_args(name, args, k.decode()[17:], task["date_done"])

        # analyse tasksets
        for k in self.r.scan_iter("celery-taskset-meta-*"):
            (name, args, date_done) = self.get_taskset_details(k.decode())
            self.add_taskid_for_taskname_and_args(name, args, k.decode()[20:], date_done)

    def get_taskset_details(self, key):
        v = self.get(key)
        if v is None:
            get_logger("RedisClient").error(f"found nothing for a taskset with {key}, shouldnt happen")
            return (None, None, None)
        try:
            task = json.loads(v)
        except json.JSONDecodeError as e:
            get_logger("RedisClient").error(f"discarding {key}, not json ? {e}")
        name = None
        args = None
        date_done = None
        for f in task['result'][1]:
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
                    get_logger("RedisClient").error(f"{name} mismatched task name for {tid}")
            if args is None:
                args = task["args"][:-1]
            # find the last finishing job
            if type(task["date_done"]) == str:
                subtask_done = datetime.fromisoformat(task["date_done"])
            else:
                subtask_done = task["date_done"]
                get_logger("RedisClient").debug(f"sd={subtask_done}, type={type(subtask_done)}")
            if date_done is None:
                date_done = subtask_done
            elif subtask_done is not None and subtask_done > date_done:
                date_done = subtask_done
            # print(f"{tid} {task['name']} {task['args'][:-1]} {task['date_done']} {date_done}")
        if name is not None:
            if name.endswith('owslayer'):
                name = 'geordash.checks.ows.owsservice'
            if name.endswith('check_res'):
                name = 'geordash.checks.mapstore.check_resources'
                args = []
            if name.endswith('check_record'):
                name = 'geordash.checks.csw.check_catalog'
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
        if 'name' in task:
            taskname = task["name"]
            args = task["args"]
        else:
            # taskset, take name & args from the first task of the set
            ftid = task['result'][1][0][0][0]
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
            if task["name"].endswith('owslayer'):
                taskname = 'geordash.checks.ows.owsservice'
            if task["name"].endswith('check_res'):
                taskname = 'geordash.checks.mapstore.check_resources'
                args = []
            if task["name"].endswith('check_record'):
                taskname = 'geordash.checks.csw.check_catalog'

        if taskname in self.task_by_taskname:
            if tuple(args) in self.task_by_taskname[taskname]:
                taskids = self.task_by_taskname[taskname][tuple(args)]
                if taskid in taskids:
                    del taskids[taskid]
                    return taskid

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
                        if 'date_done' in taskb and taskb["date_done"] is not None:
                            date_done = taskb["date_done"]
                        if not 'name' in taskb: # taskset
                            (x, y, date_done) = self.get_taskset_details("celery-taskset-meta-" + taskid)
                        if date_done is not None:
                            taskids[taskid] = { "finished": date_done }
                    found_taskids.append({'id': taskid, 'finished': taskids[taskid]["finished"] })

                # remove taskids from the in-memory list
                for t in dropped_taskids:
                    del taskids[t]
                return found_taskids
        return None

    def add_taskid_for_taskname_and_args(self, taskname, args, taskid, finished=None):
        if taskname not in self.task_by_taskname:
            self.task_by_taskname[taskname] = dict()
        if args is None: # invalid task ?
            return
        if tuple(args) not in self.task_by_taskname[taskname]:
            self.task_by_taskname[taskname][tuple(args)] = dict()
        self.task_by_taskname[taskname][tuple(args)][taskid] = {'finished': finished}

if __name__ == '__main__':
    import sys
    sys.path.append('.')
    import config
    rc = RedisClient(config.url)
    print(rc.task_by_taskname["geordash.checks.mapstore.check_res"].keys())
    print(rc.task_by_taskname["geordash.checks.mapstore.check_res"][("CONTEXT", 38)])
    print(tuple(["CONTEXT", 38]) in rc.task_by_taskname["geordash.checks.mapstore.check_res"])
    print(len(rc.get("celery-task-meta-0cbc9aee-a2ea-4933-99b9-f448fb127044")))
    print(len(rc.get("0cbc9aee-a2ea-4933-99b9-f448fb127044")))
    print(len(rc.get("celery-task-meta-489dfd21-ad1a-4317-97da-af33d4111099")))
    tasks = rc.get_taskids_by_taskname_and_args("geordash.checks.mapstore.check_res", ["MAP", 1])
    print(tasks)
    for f in tasks:
        print(len(rc.get(f['id'])))
        print(f['finished'])
        j = json.loads(rc.get(f['id']))
        print(j["result"]["problems"])
