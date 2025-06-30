# Quick reference

-    **Maintained by**:  
     [georchestra.org](https://www.georchestra.org/)

-    **Where to get help**:  
     the [geOrchestra Github repo](https://github.com/georchestra/georchestra), [IRC chat](https://matrix.to/#/#georchestra:osgeo.org), Stack Overflow

# Featured tags

- `latest`, `0.1.0`

# Quick reference

-	**Where to file issues**:  
     [https://github.com/georchestra/georchestra/issues](https://github.com/georchestra/georchestra/issues)

-	**Supported architectures**:   
     [`amd64`](https://hub.docker.com/r/amd64/docker/)

-	**Source of this description**:  
     [docs repo's directory](https://github.com/georchestra/gaia/blob/master/DOCKER_HUB.md)

# What are `georchestra/gaia` and `georchestra/gaia-celery`

**Gaia** (geOrchestra Automated Integrity Analysis) and **Gaia-celery** are the building blocks of an application which offer a dashboard to monitor the health of geOrchestra services, and to perform checks on them.

[//]: # (# How to use this image)

[//]: # (As for every other geOrchestra webapp, its configuration resides in the data directory &#40;[datadir]&#40;https://github.com/georchestra/datadir&#41;&#41;, typically something like /etc/georchestra, where it expects to find a maelstro sub-directory.)

[//]: # (It is recommended to use the official docker composition: https://github.com/georchestra/docker.)

[//]: # (For this specific component, see the section `maelstro` in the [`georchestra/docker/docker-compose.yml`]&#40;https://github.com/georchestra/docker/blob/master/docker-compose.yml&#41; file.)

## Where is it built

This image is built using docker files in repo's `docker` folder.

# License

View [license information](https://www.georchestra.org/software.html) for the software contained in this image.

As with all Docker images, these likely also contain other software which may be under other licenses (such as Bash, etc from the base distribution, along with any direct or indirect dependencies of the primary software being contained).

[//]: # (Some additional license information which was able to be auto-detected might be found in [the `repo-info` repository's georchestra/ directory]&#40;&#41;.)

As for any docker image, it is the user's responsibility to ensure that usages of this image comply with any relevant licenses for all software contained within.