Append layer to container registry image
----------------------------------------

This utility script appends a tarball to an existing container image
available in a container registry (without having to pull existing
image data).

It supports any registry that implements the [OCI Distribution
Spec](https://github.com/opencontainers/distribution-spec).


### Installation

Use the script as-is or install using pip:

```bash
$ pip install appendlayer
```

This registers the entry-point "appendlayer" which typically lets you
call it directly as an executable command.


### Authentication

The script reads an OAuth2 refresh token from the `REFRESH_TOKEN`
environment variable.

For example, for [Azure Container
Registry](https://azure.microsoft.com/en-us/services/container-registry/):

```bash
$ export REFRESH_TOKEN=$(az acr login -t --name <registry-name>.azurecr.io 2>/dev/null | \
      jq -r .accessToken)
```
(The snippet above requires [jq](https://stedolan.github.io/jq/) to print out the access token.)


### Usage

Pipe in the layer contents using a tarball and provide the repository (or _image_) name and the old and new tags:

```bash
$ echo "Hello world" > test.txt
$ tar cvf - test.txt | appendlayer <host> <repository> <old-tag> <new-tag>
```

For Azure Container Registry (ACR) for example, the _host_ is
typically `<registry-name>.azurecr.io`.
