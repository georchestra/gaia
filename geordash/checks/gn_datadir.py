#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from sqlalchemy import create_engine, MetaData, select, Column, String, Integer, Text
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.engine import URL
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.exc import NoResultFound, OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import glob
from pathlib import Path
from flask import current_app as app

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

        # Perform database reflection to analyze tables and relationships
        m = MetaData(schema=conf.get("geonetworkSchema"))
        Base = automap_base(metadata=m)
        Base.prepare(
            autoload_with=engine,
            name_for_collection_relationship=name_for_collection_relationship,
        )

        self.sessionm = sessionmaker(bind=engine)
        self.sessiono = self.sessionm()

        self.gnmetadatas = self.session().query(Metadata).all()
        # self.gnmetadatas.sort(key=lambda x: x.id)
        self.meta = []
        for foldermeta in glob.glob("/mnt/geonetwork_datadir/data/metadata_data/*/*"):
            idmeta = foldermeta.split("/")[-1]
            existing_index = 0
            for (index, item) in enumerate(self.gnmetadatas):
                if item.id == int(idmeta):
                    existing_index =index
                    break
            if existing_index:
                continue
            else:
                # append useless folder
                self.meta.append(foldermeta)

    def get_metauseless_list(self):
        return self.meta

    def process_size(self):
        total_could_be_deleted = 0
        for path in self.meta:
            total_could_be_deleted += get_folder_size(path)
        print("In total " + str(total_could_be_deleted) + " on "+ str(get_folder_size("/mnt/geonetwork_datdadir")) +" bytes could be deleted")

    def session(self):
        try:
            self.sessiono.execute(select(1))
        except OperationalError:
            print("Reconnecting to the database...")
            self.sessiono = self.sessionm()
        return self.sessiono


# GeonetworkDatadirChecker(conf)