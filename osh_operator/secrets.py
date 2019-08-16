import base64
from dataclasses import asdict, dataclass
import json
from os import urandom
from typing import Dict, Optional

import kopf
import pykube

from . import kube
from mcp_k8s_lib import ceph_api


@dataclass
class OSSytemCreds:
    username: str
    password: str


@dataclass
class OpenStackCredentials:
    database: Dict[str, OSSytemCreds]
    messaging: Dict[str, OSSytemCreds]


def handle_rgw_secret(body, meta, status, logger, diff, **kwargs):
    data = body["data"]
    keys = [
        "OS_AUTH_URL",
        "OS_DEFAULT_DOMAIN",
        "OS_INTERFACE",
        "OS_PASSWORD",
        "OS_PROJECT_DOMAIN_NAME",
        "OS_PROJECT_NAME",
        "OS_REGION_NAME",
        "OS_USER_DOMAIN_NAME",
        "OS_USERNAME",
    ]
    args = {}
    for key in keys:
        args[key[3:].lower()] = data[key]
    os_rgw_creds = ceph_api.OSRGWCreds(**args)
    ceph_api.set_os_rgw_creds(os_rgw_creds, kube.save_secret_data)


@kopf.on.create("", "v1", "secrets")
async def handle_secrets_create(body, meta, status, logger, diff, **kwargs):
    # TODO: unhardcode secret name
    logger.info(f"Handling secret create {meta['name']}")
    if meta["name"] == "ceph-keystone-user":
        handle_rgw_secret(body, meta, status, logger, diff, **kwargs)


@kopf.on.update("", "v1", "secrets")
async def handle_secrets_update(body, meta, status, logger, diff, **kwargs):
    # opentack-helm doesn't support password update by design we will need
    # to get back here when it is solved.
    pass


def get_os_service_secret(
    name: str, namespace: str
) -> Optional[OpenStackCredentials]:
    # pykube.exceptions.ObjectDoesNotExist will be handled on the layer above
    secret = kube.find(pykube.Secret, name, namespace)
    data = secret.obj["data"]

    os_creds = OpenStackCredentials(database={}, messaging={})
    for kind, creds in data.items():
        decoded = json.loads(base64.b64decode(creds))
        cr = getattr(os_creds, kind)
        for account, c in decoded.items():
            cr[account] = OSSytemCreds(
                username=c["username"], password=c["password"]
            )

    return os_creds


def save_os_service_secret(
    name: str, namespace: str, params: OpenStackCredentials
):
    data = asdict(params)

    for key in data.keys():
        data[key] = base64.b64encode(json.dumps(data[key]).encode()).decode()

    kube.save_secret_data(namespace, name, data)


def generate_password(length=32):
    """
    Generate password of defined length

    Example:
        Output
        ------
        Jda0HK9rM4UETFzZllDPbu8i2szzKbMM
    """
    chars = "aAbBcCdDeEfFgGhHiIjJkKlLmMnNpPqQrRsStTuUvVwWxXyYzZ1234567890"

    return "".join(chars[c % len(chars)] for c in urandom(length))
