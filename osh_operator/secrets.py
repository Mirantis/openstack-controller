import kopf

from . import kube
from mcp_k8s_lib import ceph_api


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
