Append layer to container registry image
----------------------------------------

This utility script appends a tarball to an existing container image
available in a container registry (without having to pull existing
image data).

It supports any registry that implements the [OCI Distribution
Spec](https://github.com/opencontainers/distribution-spec).


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
$ tar cvf - test.txt | python main.py <host> <repository> <old-tag> <new-tag>
```

For ACR, the _host_ is typically `<registry-name>.azurecr.io`.
