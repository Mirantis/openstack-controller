import kopf
from mcp_k8s_lib import ceph_api, utils

from openstack_controller import kube
from openstack_controller import secrets

LOG = utils.get_logger(__name__)


@kopf.on.create(
    "", "v1", "secrets", labels={"application": "ceph", "component": "rgw"}
)
async def handle_rgw_secret(
    body, meta, name, status, logger, diff, **kwargs,
):
    # TODO: unhardcode secret name
    LOG.debug(f"Handling secret create {name}")
    if name != secrets.RGW_KEYSTONE_SECRET:
        return
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
