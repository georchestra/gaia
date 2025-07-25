#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from owslib.wms import WebMapService
from owslib.wfs import WebFeatureService
from owslib.wmts import WebMapTileService
from owslib.csw import CatalogueServiceWeb
from owslib.fes import PropertyIsEqualTo, And
from owslib.util import ServiceException
from requests.exceptions import HTTPError, SSLError, ReadTimeout
from urllib3.exceptions import MaxRetryError
from lxml.etree import XMLSyntaxError
from time import time

from redis import Redis
import jsonpickle
import os
import sys
import threading
import json
import traceback
import requests

from geordash.logwrap import get_logger
from gsdscanner import GSDatadirScanner
from geordash.utils import find_geoserver_datadir

non_harvested = PropertyIsEqualTo("isHarvested", "false")


class CachedEntry:
    def __init__(self, stype, url):
        self.stype = stype
        self.url = url
        self.s = None
        self.records = None
        self.timestamp = None
        self.exception = None

    def nelems(self):
        if self.stype in ("wms", "wmts", "wfs"):
            return len(self.s.contents)
        else:
            if self.records:
                return len(self.records)
            else:
                return 0

    def contents(self):
        if self.stype in ("wms", "wmts", "wfs"):
            return self.s.contents
        if self.stype == "csw" and self.s is not None and self.records is None:
            self.records = dict()
            startpos = 0
            while True:
                self.s.getrecords2(
                    constraints=[non_harvested],
                    esn="full",
                    startposition=startpos,
                    maxrecords=100,
                )
                self.records |= self.s.records
                get_logger("OwsCapCache").debug(
                    f"start = {startpos}, res={self.s.results}, returned {len(self.s.records)}, mds={len(self.records)}"
                )
                startpos = self.s.results["nextrecord"]  # len(mds) + 1
                if startpos > self.s.results["matches"] or startpos == 0:
                    break
            get_logger("OwsCapCache").info(
                f"cached {len(self.records)} csw records for {self.url}"
            )
        else:
            get_logger("OwsCapCache").debug(
                f"returning {len(self.records)} cached csw records for {self.url}"
            )
        return self.records


""" poorman's in-memory capabilities cache
keep a timestamp for the last fetch, refresh every 12h by default, and
force-fetch on demand.
"""


class OwsCapCache:
    def __init__(self, conf, app):
        self.services = dict()
        self.cache_lifetime = 12 * 60 * 60
        try:
            from config import url

            self.rediscli = Redis.from_url(url)
            self.conf = conf
        except:
            get_logger("OwsCapCache").error(f"wrong can't set redis url {url}")

    def get_entry_from_redis(self, rkey, force_fetch=False):
        """
        returns a CachedEntry object, or None if not found
        """
        re = self.rediscli.get(rkey)
        if re:
            ce = jsonpickle.decode(json.loads(re.decode("utf-8")))
            # if found, only return fetched value from redis if ts is valid
            if type(ce) != CachedEntry:
                get_logger("OwsCapCache").error(
                    f"cached entry behind {rkey} isnt a CachedEntry but a {type(ce)}?"
                )
            elif ce.timestamp + self.cache_lifetime > time() and not force_fetch:
                ttl = self.rediscli.ttl(rkey)
                get_logger("OwsCapCache").debug(
                    f"returning {rkey} entry from redis cache with {ce.nelems()} items, ts={ce.timestamp} (and redis ttl {ttl})"
                )
                return ce
        return None

    def fetch(self, service_type, url, force_fetch=False):
        if service_type not in ("wms", "wmts", "wfs", "csw"):
            return None
        # check first in redis
        rkey = f"{service_type}-{url.replace('/','~')}"
        re = self.get_entry_from_redis(rkey, force_fetch)
        if re:
            self.services[service_type][url] = re
            return re

        get_logger("OwsCapCache").info(
            "fetching {} getcapabilities for {}".format(service_type, url)
        )
        entry = CachedEntry(service_type, url)
        try:
            # XX consider passing parse_remote_metadata ?
            if service_type == "wms":
                try:
                    entry.s = WebMapService(url, version="1.3.0")
                except (AttributeError, ServiceException) as e:
                    # XXX hack parses the 403 page returned by the s-p ?
                    if (
                        type(e) == ServiceException
                        and type(e.args) == tuple
                        and (
                            "interdit" in e.args[0]
                            or "401 Authorization Required" in e.args[0]
                            or "HTTP Status 401 – Unauthorized" in e.args[0]
                        )
                    ):
                        get_logger("OwsCapCache").warning("{} needs auth ?".format(url))
                        entry.exception = ServiceException("Needs authentication")
                    else:
                        err = traceback.format_exception(e, limit=-1)
                        get_logger("OwsCapCache").error(
                            f"failed loading {service_type} 1.3.0, exception catched: {err[-1]}"
                        )
                        get_logger("OwsCapCache").info("retrying with version=1.1.1")
                        entry.s = WebMapService(url, version="1.1.1")
            elif service_type == "wfs":
                entry.s = WebFeatureService(url, version="1.1.0")
            elif service_type == "csw":
                entry.s = CatalogueServiceWeb(url, timeout=60)
            elif service_type == "wmts":
                entry.s = WebMapTileService(url)
        except ServiceException as e:
            # XXX hack parses the 403 page returned by the s-p ?
            if type(e.args) == tuple and (
                "interdit" in e.args[0]
                or "401 Authorization Required" in e.args[0]
                or "HTTP Status 401 – Unauthorized" in e.args[0]
            ):
                get_logger("OwsCapCache").warning("{} needs auth ?".format(url))
                entry.exception = ServiceException("Needs authentication")
            else:
                get_logger("OwsCapCache").error(
                    f"failed loading {service_type} from {url}"
                )
                get_logger("OwsCapCache").error(e)
                entry.exception = e
            # cache the failure
            entry.s = None
        #        except (HTTPError, SSLError, ReadTimeout, MaxRetryError, XMLSyntaxError, KeyError) as e:
        except Exception as e:
            err = traceback.format_exception(e, limit=-1)
            if (
                type(e) == requests.exceptions.ConnectionError
                and "Name or service not known" in err[-1]
            ):
                get_logger("OwsCapCache").error(f"DNS not known for {url}")
            elif (
                type(e) == AttributeError
                and "'NoneType' object has no attribute 'find'" in err[-1]
            ):
                get_logger("OwsCapCache").error(
                    f"Likely not XML in capabilities at {url}"
                )
            elif "SSLError" in err[-1]:
                get_logger("OwsCapCache").error(f"SSLError for {url}")
            elif "HTTPError" in err[-1] and "404" in err[-1]:
                get_logger("OwsCapCache").error(f"404 for {url}")
            get_logger("OwsCapCache").error(
                f"failed loading {service_type} from {url}, exception catched: {type(e)}"
            )
            get_logger("OwsCapCache").error(err)
            entry.s = None
            # cache the failure
            entry.exception = e
        entry.timestamp = time()
        self.services[service_type][url] = entry
        # persist entry in redis
        self.set_entry_in_redis(rkey, entry)
        return entry

    def set_entry_in_redis(self, rkey, entry):
        if entry.exception is not None:
            json_entry = json.dumps(jsonpickle.encode(entry, unpicklable=False))
        else:
            json_entry = json.dumps(jsonpickle.encode(entry))
        self.rediscli.set(rkey, json_entry)
        self.rediscli.expire(rkey, self.cache_lifetime)
        if entry.exception is not None:
            get_logger("OwsCapCache").debug(
                f"persisted {rkey} in redis with exception {type(entry.exception)}, ttl {self.cache_lifetime}, ts={entry.timestamp}"
            )
        else:
            get_logger("OwsCapCache").debug(
                f"persisted {rkey} in redis with nelems={entry.nelems()}, ttl {self.cache_lifetime}, ts={entry.timestamp}"
            )

    def get(self, service_type, url, force_fetch=False):
        # is a relative url, prepend https://domainName
        if not url.startswith("http"):
            url = "https://" + self.conf.get("domainName") + url
        if service_type not in self.services:
            self.services[service_type] = dict()
        if url not in self.services[service_type]:
            return self.fetch(service_type, url, force_fetch)
        else:
            ce = self.services[service_type][url]
            if ce.timestamp + self.cache_lifetime > time() and not force_fetch:
                if ce.s == None:
                    get_logger("OwsCapCache").warning(
                        f"already got a {type(ce.exception)} for {service_type} {url} in cache, returning cached failure"
                    )
                    return ce
                if service_type == "csw":
                    rkey = f"{service_type}-{url.replace('/','~')}"
                    re = self.get_entry_from_redis(rkey)
                    if re is None:
                        get_logger("OwsCapCache").info(
                            f"redis key {rkey} doesnt exist but we have a (probably invalid now) in-memory entry for {service_type} {url}, refreshing"
                        )
                        return self.fetch(service_type, url, force_fetch)
                    if re and re.records is None and ce.records is not None:
                        get_logger("OwsCapCache").info(
                            f"updating redis key {rkey} with {ce.nelems()} cached records"
                        )
                        self.set_entry_in_redis(rkey, ce)
                    if re and re.records is not None and ce.records is None:
                        get_logger("OwsCapCache").debug(
                            f"our in-memory csw cached entry for {url} had no records and the one in redis with {rkey} has {re.nelems()}, updating our local one"
                        )
                        self.services[service_type][url] = re
                        ce = re
                get_logger("OwsCapCache").debug(
                    f"returning {service_type} getcapabilities from process in-memory cache for {url} with {ce.nelems()} entries, ts={ce.timestamp}"
                )
                return ce
            else:
                if force_fetch:
                    get_logger("OwsCapCache").info(
                        f"force-fetching {service_type} getcapabilities from {url}"
                    )
                elif ce.timestamp + self.cache_lifetime > time():
                    get_logger("OwsCapCache").info(
                        f"cached entry for {service_type} {url} expired (ts={ce.timestamp}), refetching"
                    )
                return self.fetch(service_type, url, True)

    def forget(self, stype, url):
        if not url.startswith("http"):
            url = "https://" + self.conf.get("domainName") + url
        if stype in self.services and url in self.services[stype]:
            get_logger("OwsCapCache").debug(
                f"deleting {url} from {stype} in-memory cache, ts was {self.services[stype][url].timestamp}"
            )
            del self.services[stype][url]
        rkey = f"{stype}-{url.replace('/','~')}"
        re = self.rediscli.get(rkey)
        if re:
            get_logger("OwsCapCache").debug(f"deleting {rkey} from capabilities cache")
            return self.rediscli.delete(rkey)
        else:
            get_logger("OwsCapCache").debug(f"{rkey} not found in capabilities cache ?")
            return 0

    def get_mviewer_configs(self):
        re = self.rediscli.get("mviewer_configs")
        if re:
            return jsonpickle.decode(json.loads(re.decode("utf-8")))
        else:
            return None

    def set_mviewer_configs(self, confs):
        json_entry = json.dumps(jsonpickle.encode(confs))
        return self.rediscli.set("mviewer_configs", json_entry)

    def get_geoserver_datadir_view(self, defpath=None):
        """check in local memory if we have a GSDatadirScanner object,
        if not, check in redis. If not found in redis, create one (async?)
        """
        if "geoserver_datadir" not in self.services:
            # XX put path and hostname in rkey ?
            rkey = "geoserver_datadir"
            re = self.rediscli.get(rkey)
            if re:
                gsdd = jsonpickle.decode(json.loads(re.decode("utf-8")))
                # update local version, this one is populated
                self.services[rkey] = gsdd
            else:
                # return a dummy unparsed one
                gsdd = GSDatadirScanner(find_geoserver_datadir(defpath))
                return gsdd

        return self.services["geoserver_datadir"]

    def update_geoserver_datadir_view(self, gsdd: GSDatadirScanner):
        rkey = "geoserver_datadir"
        json_entry = json.dumps(jsonpickle.encode(gsdd))
        self.rediscli.set(rkey, json_entry)
        # update local version
        self.services[rkey] = gsdd
