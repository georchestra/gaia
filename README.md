# gaia (geOrchestra Automated Integrity Analysis) - a geOrchestra dashboard

# Summary

## the problem

The SDI data admin's life looks like and enless quest for consistency. He/she has to deal with loosely linked and perpetually moving datas, metadatas, services and maps published on numerous platforms. However, all this information is structured according to OGC standards. Thus most of the tests that the admin does manually can be automated. And most of the information, even if it comes from different platforms, can be presented in a synthetic way to obtain an ongoing evaluation of the problems, and save a lot of time on corrections.

## the response

This project aims at providing a data quality insurance dashboard for [geOrchestra](https://georchestra.org), to make the data or map admin's life easier. Some of the GAIA benefits :

**Automated inventory** : GAIA scans interactively and periodically and interactively the catalogs, services and maps, and displays all those contents in one place. You get a birdeye view on all contents.

**Integrity check** : GAIA performs content analysis : missing or unreachable metadatas, bad OGC services, http errors, inconsistencies between metadadas and services ... reusing what was done in  [sdi-consistency-check](https://github.com/georchestra/sdi-consistence-check/).

**Admin helper** : You want to fix an error. GAIA let you access instantly the admin page, modify settings and check again the ressource

**API** : GAIA returns all results as JSON so you can use this data in your own tools

## detailed features

- clean and fine-grained URLs for all ressources
- returns results in HTML pages or JSON
- checks for common errors
- give direct access to data/metadata/map previews
- give direct access to data/metadata/map administration pages
- can use geOrchestra roles
- performs scheduled scans
- performs on demand scans

## dependencies

Here are the dependencies and why they are needed :

- the web interface : [flask 2.2](https://flask.palletsprojects.com/en/2.2.x/) and [flask-bootstrap](https://bootstrap-flask.readthedocs.io/en/stable/)
- the job queue to run the checks in background tasks : [celery 5.2](https://docs.celeryq.dev/en/v5.2.6/)
- interaction with the sql database: [sqlalchemy 1.4](https://docs.sqlalchemy.org/en/14/) and [psycopg2](https://www.psycopg.org/)
- interaction with the WMS/WFS/WMTS/CSW services: [owslib](https://owslib.readthedocs.io/en/latest/)
- serializing the capabilities of the services: [jsonpickle](https://jsonpickle.github.io/)
- and finally caching them to avoid hammering the services again and again : [redis](https://redis.io/docs/latest/develop/connect/clients/python/redis-py/)

## developpment status

it is a work in progress, being developed when spare time is available. for now
developped in my own github account, but if enough features are developed and
interest is shown, it'll move to the
[geOrchestra](https://github.com/georchestra/) organization.

# installation

## debian installation

GAIA is being written using the versions of python/flask/celery provided by debian 12, it should only require 'recent' versions of those:

```
apt install python3-flask-bootstrap python3-flask python3-celery python3-sqlalchemy \
    python3-psycopg2 python3-owslib python3-jsonpickle python3-redis python3-psutil python3-gdal gunicorn
```

## virtualenv installation

GAIA runs in a python virtualenv >= 3.10 with the provided <code>requirements.txt</code>

```
python -m virtualenv venv
source ./venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
./run.sh
```

## system installation

run `install.sh`, which will:
- create a `gaia` unix group
- create `celery` and `gunicorn` unix users belonging to `gaia` group
- install two systemd units, properly setting the path to where the code was deployed

once installed, gaia needs two systemd services running:
- `gaia-gunicorn` for the web ui, accessed at `https://<idsurl>/gaia/`
- `gaia-celery` for the celery worker, used for long-running checks

# configuration

## geOrchestra integration

the web service should be added behind geOrchestra's security-proxy/gateway, so
that it knows the connected user and can display user-tailored information.

add this line to `/etc/georchestra/security-proxy/target-mappings.properties` to declare GAIA in the geOrchestra security proxy :
```
gaia=http://<hostname>:<port>/gaia/
```

and visit https://<sdiurl>/gaia/, which should list for now:
- your metadatas
- the maps & contexts you can access

if your datadir isn't in `/etc/georchestra`, point the `georchestradatadir`
environment variable to the path where your datadir is located.

the datadir is used to:
- [configure the header](geordash/__init__.py#L62) and find the [fully-qualified domain name](geordash/dashboard.py#L129) (used in several places) from `default.properties`
- find out the [path for geonetwork/geoserver](geordash/__init__.py#L60) from mapstore's `localgs`/`local` entries in `mapstore/configs/localConfig.json`. if not found, will default to `/geonetwork/` and `/geoserver/`.
- find how to [connect to the mapstore schema](geordash/checks/mapstore.py#L41) from `mapstore/geostore.properties`
- find where are mapstore/geoserver/geonetwork, eg their direct url:port behind the S-P by reading `security-proxy/target-mappings.properties` (cf the calls to `conf.get("xxx", "secproxytargets")` in [that file](geordash/api.py))
- some work is probably required to achieve the same with the yaml config for the gateway
- this is used to query them directly on behalf of the currently connected user
- the datadir files are analyzed/parsed [here](geordash/georchestraconfig.py#L15)

## cache

for now a redis instance is used for celery's broker/result backend storage, to
configure in [`config.py`](config.py.example) - celery can use rabbitmq for the
broker, and in the end the geOrchestra PostgreSQL database will be used to
store task results.

it tries as much as possible to autoconfigure itself by reading configuration
files from [geOrchestra's datadir](https://github.com/georchestra/datadir)


## services configuration

the configuration has to be done:
- in [`gunicorn.conf.py`](gunicorn.conf.py.example) for gunicorn options
- in [`celeryconfig.py`](geordash/celeryconfig.py.example) for celery configuration/options

the [`env`](env.example) file should also contain options used to start celery, and during
development both services can be started by `run.sh`, which:

- starts a `celery` process in the background (with its loglevel set according to CELERY_LOGLEVEL)
- starts a `flask` process in foreground with debug levels set to the maximum.

it is also possible to start a gunicorn process manually instead of flask via
```
gunicorn --log-level DEBUG 'geordash:create_app()'
```

# Usage

## pages

here's a quick list of pages/routes implemented so far, the goal is to have as
much interlinking as possible.

the logic behind each url/route is that if you know what you want to access, be
it a given OGC layer by its short name, a metadata by its uuid, or a mapstore
map by its numeric id, you should be able to directly access it by typing the
url in your browser.

### `/`
shows cards with results of the last check for:
- all geoserver WMS layers
- all geoserver WFS layers
- all geonetwork metadatas

if the user is a superuser:
- all mapstore maps
- all mapstore contexts

instead, amount of maps/contexts that the current user can access.

### `/my-metadata`
- lists the metadata a user with ROLE_GN_EDITOR can edit

### `/my-maps-and-apps`
- lists the mapstore maps and context the current user can access
- whether he is connected and has been granted access to/created some content
- or the public content that is available

### `/admin/mapstore/configs`
- lists current problems on mapstore configuration files in the datadir (`new.json`, `config.json`, `localConfig.json`)

### `/admin/mapstore/maps`
- lists all maps in a table, with their owner/ACL information
- lists current problems on the maps
- allows to manually trigger a check for the integrity of all maps

### `/admin/mapstore/contexts`
- lists all contexts in a table, with their owner/ACL information
- lists current problems on the contexts
- allows to manually trigger a check for the integrity of all contexts

### `/admin/mviewer/configs`
- lists all known mviewer configs in a table, with links to view/forget about them
- lists current problems on the configs
- allows to manually trigger a check for the integrity of all known configs

### `/admin/geonetwork`
- lists currently configured portals in geonetwork

### `/admin/geoserver`
- lists currently configured workspaces in geoserver, querying geoserver's REST API

### `/admin/geoserver/datadir`
- display geoserver datadir contents, from a high pov - more details [documented here](gsdscanner/README.md)

### `/admin/geoserver/datadir/<itemtype>`
- display list of geoserver items for the given type (workspaces, datastores, layers, styles...)

### `/admin/geoserver/datadir/<itemtype>/<itemid>`
- displays details about a given item in the geoserver datadir

### `/map/<mapid>`
- displays map details & current problems
- links to the OGC layers used by the map

### `/mviewer/<map config url>`
- displays mviewer config details & current problems
- links to the OGC layers used by the map for themes and backgrounds

### `/ctx/<mapid>`
- displays ctx map details & current problems
- links to the OGC layers used by the ctx map

### `/ows/<{wms,wfs,wmts}>/<service url>/`
- displays contents of a given OGC service
- shows the list of all problems for all layers in the service
- `service url` is an url with slashes replaced by `~`, eg `~geoserver~wms` for the default WMS geoserver, `~geoserver~workspace~ows` for a workspace
- full urls such as `https:~~wmts.craig.fr~pci~service` can be used, if the `https:~~fqdn` part is omitted the georchestra FQDN is assumed

### `/ows/<{wms,wfs,wmts}>/<service url>/<layername>`
- displays the details about a given layer in a given OGC service
- links to the mapstore maps & contexts that use this layer
- links to the metadata page
- allow to preview the layer in geoserver, or open it in mapstore
- links to the geoserver layer edit page
- shows the list of all problems for all layers in the service

### `/csw/<portal>`
- displays the lists of metadatas in a given CSW portal, eg `/csw/srv` for all
  metadatas, and if you've created an `opendata` portal then `/csw/opendata`
  lists the metadatas in this CSW endpoint.

### `/csw/<portal>/<uuid>`
- displays the details about a given metadata in a given CSW portal
- allows to view the metadata in datahub/geonetwork
- links to the editor view in geonetwork
- links to the OGC:W{M,F}S layers listed in the metadata



