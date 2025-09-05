#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
import json

import requests
from requests.exceptions import ReadTimeout

from celery import shared_task
from celery import Task
from celery import group

from geordash.logwrap import get_logger
from geordash.owscapcache import OwsCapCache

from owslib.fes import PropertyIsEqualTo, And

from flask import current_app as app
from geordash.utils import find_localmduuid, unmunge, objtype


from sqlalchemy import create_engine, MetaData, select, Column, String, Integer, Text
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.engine import URL
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.exc import NoResultFound, OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta
import glob
from pathlib import Path


Base = declarative_base()

# Define the Metadata model (example schema of a GeoNetwork metadata table)
class Metadata(Base):
    __tablename__ = "metadata"
    __table_args__ = {"schema": "geonetwork"}
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True)
    data = Column(Text)  # Metadata content (e.g., XML or JSON)
    schemaid = Column(String)  # Metadata schema (e.g., ISO 19115)
    isharvested = Column(Integer)

def get_folder_size(folder):
    return ByteSize(sum(file.stat().st_size for file in Path(folder).rglob('*')))

class ByteSize(int):
    _KB = 1024
    _suffixes = 'B', 'KB', 'MB', 'GB', 'PB'

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        self.bytes = self.B = int(self)
        self.kilobytes = self.KB = self / self._KB ** 1
        self.megabytes = self.MB = self / self._KB ** 2
        self.gigabytes = self.GB = self / self._KB ** 3
        self.petabytes = self.PB = self / self._KB ** 4
        *suffixes, last = self._suffixes
        suffix = next((
            suffix
            for suffix in suffixes
            if 1 < getattr(self, suffix) < self._KB
        ), last)
        self.readable = suffix, getattr(self, suffix)

        super().__init__()

    def __str__(self):
        return self.__format__('.2f')

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, super().__repr__())

    def __format__(self, format_spec):
        suffix, val = self.readable
        return '{val:{fmt}} {suf}'.format(val=val, fmt=format_spec, suf=suffix)

    def __sub__(self, other):
        return self.__class__(super().__sub__(other))

    def __add__(self, other):
        return self.__class__(super().__add__(other))

    def __mul__(self, other):
        return self.__class__(super().__mul__(other))

    def __rsub__(self, other):
        return self.__class__(super().__sub__(other))

    def __radd__(self, other):
        return self.__class__(super().__add__(other))

    def __rmul__(self, other):
        return self.__class__(super().__rmul__(other))
conf = {
    'pgsqlUser': 'georchestra',
    'pgsqlHost': '127.0.0.1',
    'pgsqlPort': '5432',
    'pgsqlPassword': 'georchestra',
    'pgsqlDatabase': 'georchestra',
    'geonetworkSchema': 'geonetwork'
}

# solves conflicts in relationship naming ?
def name_for_collection_relationship(base, local_cls, referred_cls, constraint):
    name = referred_cls.__name__.lower()
    local_table = local_cls.__table__
    # print("local_cls={}, local_table={}, referred_cls={}, will return name={}, constraint={}".format(local_cls, local_table, referred_cls, name, constraint))
    if name in local_table.columns:
        newname = name + "_"
        print("Already detected name %s present.  using %s" % (name, newname))
        return newname
    return name

class GeonetworkDatadirChecker:
    def __init__(self, conf):
        url = URL.create(
            drivername="postgresql",
            username=conf.get("pgsqlUser"),
            host=conf.get("pgsqlHost"),
            port=conf.get("pgsqlPort"),
            password=conf.get("pgsqlPassword"),
            database=conf.get("pgsqlDatabase"),
        )

        engine = create_engine(url)
        self.sessionm = sessionmaker(bind=engine)
        self.sessiono = self.sessionm()

        # Perform database reflection to analyze tables and relationships
        m = MetaData(schema=conf.get("geonetworkSchema"))
        Base = automap_base(metadata=m)
        Base.prepare(
            autoload_with=engine,
            name_for_collection_relationship=name_for_collection_relationship,
        )
        self.allmetadatas = self.session().query(Metadata).all()
        # for (index, item) in enumerate(self.allmetadatas):
        #     get_logger("CheckGNDatadir").debug("test1")

    def session(self):
        try:
            self.sessiono.execute(select(1))
        except OperationalError:
            print("Reconnecting to the database...")
            self.sessiono = self.sessionm()
        return self.sessiono

    def refresh_meta_list(self):
        self.allmetadatas = self.session().query(Metadata).all()

    def get_meta_list(self):
        return self.allmetadatas

@shared_task(bind=True)
def check_gn_meta(self):
    get_logger("CheckGNDatadir").debug("Start gn datadir checker")
    metadatabase = app.extensions["gndc"]
    gnmetadatas = metadatabase.get_meta_list()
    geonetwork_datadir_path = app.extensions['conf'].get("geonetwork.dir", "geonetwork")
    # self.gnmetadatas.sort(key=lambda x: x.id)
    meta = dict()
    meta["problems"] = list()
    total_could_be_deleted = 0
    for foldermeta in glob.glob(geonetwork_datadir_path+"/data/metadata_data/*/*"):
        idmeta = foldermeta.split("/")[-1]
        get_logger("CheckGNDatadir").debug(foldermeta)
        existing_index = 0

        for (index, item) in enumerate(gnmetadatas):

            if item.id == int(idmeta):
                existing_index = index
                break
        if existing_index:
            continue
        else:
            # append useless folder
            meta["problems"].append(
                {
                    "type": "UnusedFileRes",
                    "path": foldermeta,
                    "size" : str(get_folder_size(foldermeta))

                }
            )
            total_could_be_deleted += get_folder_size(foldermeta)
    get_logger("CheckGNDatadir").debug("finish gn datadir checker")
    if not len(meta):
        meta["problems"].append(
        {
            "type": "UnusedFileResNone",
            "path": "None",
            "size": "0 KB",
        })
    else:
        meta["problems"].append(
        {
            "type": "UnusedFileResTotal",
            "path": "Total",
            "size": str(total_could_be_deleted),
            "total": str(get_folder_size(geonetwork_datadir_path))
        })

    return meta



# GeonetworkDatadirChecker(conf)