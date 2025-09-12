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
import jinja2

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
    return sum(file.stat().st_size for file in Path(folder).rglob('*'))

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
    geonetwork_dir_path = app.extensions['conf'].get("geonetwork.dir", "geonetwork")
    geonetwork_datadir_path = app.extensions['conf'].get("geonetwork.data.dir", "geonetwork").replace("${geonetwork.dir}", geonetwork_dir_path)
    # self.gnmetadatas.sort(key=lambda x: x.id)
    meta = dict()
    meta["problems"] = list()
    total_could_be_deleted = 0
    for foldermeta in glob.glob(geonetwork_datadir_path+"*/*"):
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
                    "size" : jinja2.Template("{{ bytes | filesizeformat }}").render(bytes=get_folder_size(foldermeta))
                }
            )
            total_could_be_deleted += get_folder_size(foldermeta)
    get_logger("CheckGNDatadir").debug("finish gn datadir checker")

    if len(meta["problems"]) > 0:
        meta["problems"].append(
        {
            "type": "UnusedFileResTotal",
            "path": "Total",
            "size": jinja2.Template("{{ bytes | filesizeformat }}").render(bytes=total_could_be_deleted),
            "total": jinja2.Template("{{ bytes | filesizeformat }}").render(bytes=get_folder_size(geonetwork_dir_path))
        })

    return meta
