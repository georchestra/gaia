#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from configparser import ConfigParser
from itertools import chain
from os import getenv, getcwd
import json
import re
import pprint

class GeorchestraConfig:
    def __init__(self):
        self.sections = dict()
        self.datadirpath = getenv("georchestradatadir", "/etc/georchestra")
        parser = ConfigParser()
        with open(f"{self.datadirpath}/default.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.sections["default"] = parser["section"]
        self.sections["default"]["datadirpath"] = self.datadirpath
        with open(f"{self.datadirpath}/mapstore/geostore.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.sections["mapstoregeostore"] = parser["section"]
        with open(
            f"{self.datadirpath}/security-proxy/targets-mapping.properties"
        ) as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.sections["secproxytargets"] = parser["section"]
        self.sections["urls"] = dict()
        with open(f"{self.datadirpath}/mapstore/configs/localConfig.json") as file:
            s = file.read()
            localconfig = json.loads(s)
            # used to find geonetwork entry in sec-proxy targets
            try:
                localentry = localconfig["initialState"]["defaultState"]["catalog"][
                    "default"
                ]["services"]["local"]
                self.sections["urls"]["localgn"] = localentry["url"].split("/")[1]
            except:
                # safe default value
                self.sections["urls"]["localgn"] = "geonetwork"
            try:
                localentry = localconfig["initialState"]["defaultState"]["catalog"][
                    "default"
                ]["services"]["localgs"]
                self.sections["urls"]["localgs"] = localentry["url"].split("/")[1]
            except:
                # safe default value
                self.sections["urls"]["localgs"] = "geoserver"
        with open(f"{self.datadirpath}/geonetwork/geonetwork.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.sections["geonetwork"] = parser["section"]
        
        # read current commit from .git/HEAD which might lead to the branch tip
        prefix = getcwd() + "/.git/"
        self.sections["gaia"] = {"commit": None}
        try:
            with open(prefix + "HEAD", "r") as head:
                branchref = head.read()
            # we're on a tag that's a git sha
            if re.match("^[0-9a-f]{32,}$", branchref):
                self.sections["gaia"] = {"commit": branchref[0:8]}
            # else we're on a branch
            elif re.match("^ref: refs/heads/.*$", branchref):
                with open(prefix + branchref.split(" ")[1].strip(), "r") as branch:
                    self.sections["gaia"] = {"commit": branch.read().strip()[0:8]}
        except OSError:
            # failed to read .git/HEAD or .git/refs/heads/* ?
            pass

    def tostr(self):
        # pp = pprint.PrettyPrinter(indent=4)
        # return pp.pprint(self.sections)

        str = ""
        for key in self.sections:
            str += key + ":\r\n<br>"
            for key2 in self.sections[key]:
                str += " \t&emsp;" + key2 + " : "
                str+= " \t&emsp;" + self.sections[key][key2] + " = " + self.get(key2, section=key) + "\r\n<br> "
        print(type(str))
        print(f"Keys in string: {str}")
        return str

    def get(self, key, section="default"):
        if section not in self.sections:
            return None
        value = self.sections[section].get(key, None)
        if value:
            # this is to catch ${ENV_VAR}
            search_env = re.match("^\${(.*)}$", value)
            # this is for url using env var http://${ENV_VAR}/geonetwork/..etc?params
            search_env2 = re.match("(.*)\${(.*)}(.*)", value)
            if search_env:
                if getenv(search_env.group(1)):
                    value = getenv(search_env.group(1))
            elif search_env2:
                if getenv(search_env2.group(2)):
                    value = (
                        search_env2.group(1)
                        + getenv(search_env2.group(2))
                        + search_env2.group(3)
                    )
        return value
