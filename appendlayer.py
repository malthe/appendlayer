import io
import os
import sys
import logging

from _thread import interrupt_main
from gzip import compress
from hashlib import sha256
from json import dumps, loads
from mmap import mmap
from tempfile import NamedTemporaryFile
from threading import Semaphore, Thread
from traceback import print_exc

from urllib.error import HTTPError
from urllib.request import (
    Request,
    urlopen,
)

BUFFER_SIZE = 2 ** 24
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
LOGGER = logging.getLogger(__name__)


def parse(response, count=None, **kwargs):
    data = response.read(count)
    return loads(data.decode("utf-8"), **kwargs)


def make_req(host, path, auth=None, method="GET", data=None, **headers):
    request = Request(
        f"https://{host}{path}", method=method, data=data, headers=headers
    )
    request.add_unredirected_header("Authorization", f"Bearer {auth}")
    if data is not None and isinstance(data, bytes):
        request.add_unredirected_header("Content-Length", str(len(data)))

    return urlopen(request)


def make_req_json(*args, **kwargs):
    return parse(make_req(*args, **kwargs))


def authenticate(host, scope):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    refresh_token = REFRESH_TOKEN
    if refresh_token is None:
        r = make_req_json(
            host,
            "/oauth2/exchange",
            method="POST",
            data=f"grant_type=access_token&access_token={ACCESS_TOKEN}&service={host}".encode("ascii"),
            **headers,
        )
        refresh_token = r["refresh_token"]

    r = make_req_json(
        host,
        "/oauth2/token",
        method="POST",
        data=f"grant_type=refresh_token&service={host}&scope={scope}&refresh_token={refresh_token}".encode(
            "ascii"
        ),
        **headers,
    )

    return r["access_token"]


def make_digest(data):
    return "sha256:" + sha256(data).hexdigest()


def upload(host, repository, auth, data, digest=None):
    prepare_upload = make_req(
        host, f"/v2/{repository}/blobs/uploads/", auth, method="POST"
    ).headers
    if digest is None:
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


def copy_blob(old_host, old_auth, old_repository, new_host, new_auth, new_repository, blob_digest):
    r = make_req(
        old_host,
        f"/v2/{old_repository}/blobs/{blob_digest}",
        old_auth,
        **{"Accept": "application/octet-stream"},
    )

    content_length = r.getheader("Content-Length")
    LOGGER.info("Copying missing blob: %s (%s bytes)", blob_digest, content_length)

    headers = {
        "Content-Length": content_length,
        "Content-Type": r.getheader("Content-Type"),
    }

    with NamedTemporaryFile(buffering=0) as f:
        length = int(r.getheader("Content-Length"))
        f.truncate(length)
        m = mmap(f.fileno(), length)
        s = Semaphore(value=0)

        def upload_blob():
            def read():
                total = 0
                digest = sha256()
                while total < length:
                    s.acquire()
                    offset = total
                    data = m[offset : offset + BUFFER_SIZE]
                    digest.update(data)
                    total += len(data)
                    yield data
                assert f"sha256:{digest.hexdigest()}" == blob_digest

            data = read()

            try:
                assert (
                    upload(new_host, new_repository, new_auth, data, digest=blob_digest)
                    is not None
                )
            except:
                print_exc()
                interrupt_main()

        thread = Thread(target=upload_blob)
        thread.start()

        b = bytearray(BUFFER_SIZE)
        total = 0
        while True:
            read = r.readinto(b)
            if not read:
                break
            f.write(b)
            s.release()
            total += read

        thread.join()


def run(old_image, new_image):
    old_host, old_image = old_image.split("/", 1)
    new_host, new_image = new_image.split("/", 1)
    old_repository, old_tag = old_image.split(":")
    new_repository, new_tag = new_image.split(":")
    old_auth = authenticate(old_host, f"repository:{old_repository}:*")
    new_auth = old_auth
    if old_host != new_host or old_image != new_image:
        new_auth = authenticate(new_host, f"repository:{new_repository}:*")
    manifest = make_req_json(
        old_host,
        f"/v2/{old_repository}/manifests/{old_tag}",
        old_auth,
        **{"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
    )

    layer_data = sys.stdin.buffer.read()
    diff_id = make_digest(layer_data)
    compressed = compress(layer_data)
    compressed_layer_digest = upload(new_host, new_repository, new_auth, compressed)
    config = make_req_json(
        old_host, f"/v2/{old_repository}/blobs/{manifest['config']['digest']}", old_auth
    )
    config["rootfs"]["diff_ids"].append(diff_id)
    config_serialized = dumps(config).encode("utf-8")
    config_digest = upload(new_host, new_repository, new_auth, config_serialized)

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

    while True:
        try:
            make_req(
                new_host,
                f"/v2/{new_repository}/manifests/{new_tag}",
                new_auth,
                method="PUT",
                data=dumps(manifest).encode("utf-8"),
                **{
                    "Content-Type": "application/vnd.docker.distribution.manifest.v2+json",
                },
            )
        except HTTPError as error:
            if error.status != 400:
                raise
            r = error
        else:
            break

        missing_blobs = []

        def hook(info):
            if info["code"] == "MANIFEST_BLOB_UNKNOWN":
                blob_digest = info["detail"]
                if blob_digest:
                    missing_blobs.append(blob_digest)
            else:
                LOGGER.error("Unexpected error: %s", info["message"])
                raise RuntimeError()

        try:
            parse(r, count=1024, object_hook=hook)
        except:
            pass

        # Unexpected error mode; re-raise error.
        if not missing_blobs:
            LOGGER.warn("Unexpected error")
            raise r

        for blob_digest in missing_blobs:
            copy_blob(old_host, old_auth, old_repository, new_host, new_auth, new_repository, blob_digest)


def main():
    logging.basicConfig()
    handler = logging.StreamHandler(sys.stderr)
    LOGGER.setLevel(logging.INFO)
    args = sys.argv[1:]
    if len(args) > 3:
        repository = args[1]
        args = args[0], repository + ":" + args[2], repository + ":" + args[3]
    if len(args) > 2:
        args = args[0] + "/" + args[1], args[0] + "/" + args[2]
    run(*args)


if __name__ == "__main__":
    main()
