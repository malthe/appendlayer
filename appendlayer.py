import io
import os
import sys

from gzip import compress
from hashlib import sha256
from json import dumps, loads

from urllib.error import HTTPError
from urllib.request import (
    Request,
    urlopen,
)

REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]


def parse(response):
    data = response.read()
    return loads(data.decode("utf-8"))


def make_req(host, path, auth=None, method="GET", data=None, **headers):
    request = Request(
        f"https://{host}{path}", method=method, data=data, headers=headers
    )
    request.add_unredirected_header("Authorization", f"Bearer {auth}")
    if data is not None:
        request.add_unredirected_header("Content-Length", str(len(data)))

    r = urlopen(request)

    if r.status == 201:
        return

    if r.status == 202:
        return r.headers

    return parse(r)


def authenticate(host, scope):
    r = make_req(
        host,
        "/oauth2/token",
        method="POST",
        data=f"grant_type=refresh_token&service={host}&scope={scope}&refresh_token={REFRESH_TOKEN}".encode(
            "ascii"
        ),
        **{
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    return r["access_token"]


def make_digest(data):
    return "sha256:" + sha256(data).hexdigest()


def upload(host, repository, auth, data):
    prepare_upload = make_req(
        host, f"/v2/{repository}/blobs/uploads/", auth, method="POST"
    )
    digest = make_digest(data)
    make_req(
        host,
        prepare_upload["Location"] + f"&digest={digest}",
        auth,
        method="PUT",
        data=data,
        **{
            "Content-Type": "application/octet-stream",
        },
    )
    return digest


def run(host, repository, old_tag, new_tag):
    auth = authenticate(host, f"repository:{repository}:*")
    manifest = make_req(
        host,
        f"/v2/{repository}/manifests/{old_tag}",
        auth,
        **{"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
    )

    config = make_req(
        host, f"/v2/{repository}/blobs/{manifest['config']['digest']}", auth
    )

    layer_data = sys.stdin.buffer.read()
    diff_id = make_digest(layer_data)
    compressed = compress(layer_data)
    compressed_layer_digest = upload(host, repository, auth, compressed)

    config["rootfs"]["diff_ids"].append(diff_id)
    config_serialized = dumps(config).encode("utf-8")
    config_digest = upload(host, repository, auth, config_serialized)

    manifest["config"] = {
        "digest": config_digest,
        "mediaType": "application/vnd.oci.image.config.v1+json",
        "size": len(config_serialized),
    }

    manifest["layers"].append(
        {
            "digest": compressed_layer_digest,
            "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
            "size": len(compressed),
        }
    )

    make_req(
        host,
        f"/v2/{repository}/manifests/{new_tag}",
        auth,
        method="PUT",
        data=dumps(manifest).encode("utf-8"),
        **{
            "Content-Type": "application/vnd.docker.distribution.manifest.v2+json",
        },
    )


def main():
    run(*sys.argv[1:])


if __name__ == "__main__":
    main()
