#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
from celery import shared_task
from geordash.logwrap import get_logger
from flask import current_app as app
from sqlalchemy import create_engine, MetaData, select, Table
from sqlalchemy.engine import URL
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
import glob
from pathlib import Path


def get_folder_size(folder):
    return sum(file.stat().st_size for file in Path(folder).rglob("*"))


class GeonetworkDatadirChecker:
    def __init__(self, conf):
        url = URL.create(
            drivername="postgresql",
            username=conf.get("jdbc.username", "geonetwork"),
            host=conf.get("jdbc.host", "geonetwork"),
            port=conf.get("jdbc.port", "geonetwork"),
            password=conf.get("jdbc.password", "geonetwork"),
            database=conf.get("jdbc.database", "geonetwork"),
        )

        engine = create_engine(
            url,
            connect_args={
                "options": f"-csearch_path={conf.get('jdbc.schema', 'geonetwork')}"
            },
        )
        self.sessionm = sessionmaker(bind=engine)
        self.sessiono = self.sessionm()

        # Perform database reflection to analyze tables and relationships
        m = MetaData(schema=conf.get("jdbc.schema", "geonetwork"))
        Table("metadata", m, autoload_with=engine)
        Base = automap_base(metadata=m)
        Base.prepare()
        self.Metadata = Base.classes.metadata

    def session(self):
        try:
            self.sessiono.execute(select(1))
        except OperationalError:
            print("Reconnecting to the database...")
            self.sessiono = self.sessionm()
        return self.sessiono

    def get_meta_list(self):
        return self.session().query(self.Metadata).all()


@shared_task(bind=True)
def check_gn_meta(self):
    get_logger("CheckGNDatadir").debug("Start gn datadir checker")
    metadatabase = app.extensions["gndc"]
    gnmetadatas = metadatabase.get_meta_list()
    geonetwork_dir_path = app.extensions["conf"].get("geonetwork.dir", "geonetwork")
    geonetwork_datadir_path = (
        app.extensions["conf"]
        .get("geonetwork.data.dir", "geonetwork")
        .replace("${geonetwork.dir}", geonetwork_dir_path)
    )
    # self.gnmetadatas.sort(key=lambda x: x.id)
    meta = dict()
    meta["searching_path"] = geonetwork_datadir_path
    meta["problems"] = list()
    total_could_be_deleted = 0
    for foldermeta in glob.glob(geonetwork_datadir_path + "*/*"):
        idmeta = foldermeta.split("/")[-1]
        subpath = foldermeta.split("/")[-2]
        get_logger("CheckGNDatadir").debug(foldermeta)
        existing_index = 0

        for index, item in enumerate(gnmetadatas):
            if item.id == int(idmeta):
                existing_index = index
                break
        if existing_index:
            continue
        else:
            # append useless folder
            meta["problems"].append(
                {
                    "url": subpath + "/" + idmeta,
                    "problem": get_folder_size(foldermeta),
                }
            )
            total_could_be_deleted += get_folder_size(foldermeta)
    get_logger("CheckGNDatadir").debug("finish gn datadir checker")

    if len(meta["problems"]) > 0:
        meta["problems"].append(
            {
                "type": "UnusedFileResTotal",
                "size": total_could_be_deleted,
                "total": get_folder_size(geonetwork_datadir_path),
            }
        )

    return meta
