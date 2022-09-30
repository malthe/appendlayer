Append layer
------------

[![PyPI version](https://badge.fury.io/py/appendlayer.svg)](https://badge.fury.io/py/appendlayer)

This standalone utility appends a tarball to an existing image in a
container registry – without having to pull down the image locally.

It supports any registry that implements the [OCI Distribution
Spec](https://github.com/opencontainers/distribution-spec).


### Why

The basic use-case for this utility is when you have a base image that
is already available in a container registry, and you simply need to
add one or more files, then push the result back to the same registry.

In this case, you can do no better in terms of network transfer than
this utility. It does the minimum amount of work in order to get the
job done.

With the [Docker
ADD](https://docs.docker.com/engine/reference/builder/#add) command,
you'd have to download the existing image and start up a build process
in order to run the `ADD` command.

```dockerfile
FROM apache/airflow:2.3.2
ADD your_tar_file.tar.gz /opt/airflow/dag
```

The resulting image would be exactly the same, but there is no special
optimization in Docker that would avoid downloading the base image
(although theoretically, it could be done but it would require bigger
changes in the data model in order to support lazy referencing of
layer data).

Incidentally, the script was designed exactly with [Apache
Airflow](https://airflow.apache.org/) in mind.


Note that Buildkit [will have support for
this](https://github.com/moby/buildkit/issues/2414) from v0.10 but
it's not clear how this will be supported in a Dockerfile.

### Installation

Install the tool using pip:

```bash
$ pip install appendlayer
```

This makes available "appendlayer" as a script in your environment.

Alternatively, download the [appendlayer.py](./appendlayer.py) script
and run it using Python directly:

```bash
$ python appendlayer.py
```

The script has no external dependencies, using only what's included already with Python.


### Usage

Pipe in the layer contents using a tarball and provide the repository (or _image_) name and the old and new tags:

```bash
$ echo "Hello world" > test.txt
$ tar cvf - test.txt | appendlayer <host> <repository> <old-tag> <new-tag>
```

Alternatively, qualify source and destination using image syntax:
```bash
$ tar cvf - test.txt | appendlayer <host> <old-repository>:<old-tag> <new-repository>:<new-tag>
```

Or even across different hosts:
```bash
$ tar cvf - test.txt | appendlayer <old-host>/<old-repository>:<old-tag> <new-host>/<new-repository>:<new-tag>
```

For Azure Container Registry (ACR) for example, the _host_ is
typically `<registry-name>.azurecr.io`.


### Authentication

The script uses OAuth2 to authorize requests to the container
registry.

This is configured using either the `ACCESS_TOKEN` or `REFRESH_TOKEN`
environment variable, or by extracting a refresh token from the Docker
configuration file (located based on the `DOCKER_CONFIG` environment
variable).

For example, for [Azure Container
Registry](https://azure.microsoft.com/en-us/services/container-registry/),
to authorize to a specific container registry.

```bash
$ export REFRESH_TOKEN=$( \
      az acr login -t --name <registry-name>.azurecr.io \
      --expose-token --output tsv --query accessToken)
```

To authorize across multiple registries, use an access token:

```bash
$ export ACCESS_TOKEN=$( \
       az account get-access-token --query accessToken --output tsv)
```
