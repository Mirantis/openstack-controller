import kopf
from mcp_k8s_lib import ceph_api, utils

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import secrets
from openstack_controller import settings  # noqa

LOG = utils.get_logger(__name__)

AUTH_KEYS = [
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


@kopf.on.create(
    "", "v1", "secrets", labels={"application": "ceph", "component": "rgw"}
)
async def handle_rgw_secret(
    body, meta, name, status, logger, diff, **kwargs,
):
    # TODO: unhardcode secret name
    LOG.debug(f"Handling secret create {name}")
    if name != constants.RGW_KEYSTONE_SECRET:
        return
    data = body["data"]
    args = {}
    for key in AUTH_KEYS:
        args[key[3:].lower()] = data[key]
    os_rgw_creds = ceph_api.OSRGWCreds(**args)
    ceph_api.set_os_rgw_creds(os_rgw_creds, kube.save_secret_data)


@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "neutron", "component": "server"},
)
async def handle_neutron_secret(
    body, meta, name, status, logger, diff, **kwargs,
):
    if name != constants.NEUTRON_KEYSTONE_SECRET:
        return

    LOG.debug(f"Handling secret create/update {name}")

    secret_data = {}
    for key in AUTH_KEYS:
        secret_data[key[3:].lower()] = body["data"][key]

    tfs = secrets.TungstenFabricSecret()
    tfs.save(secret_data)


@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "keystone", "component": "server"},
)
async def handle_keystone_secret(
    body, meta, name, status, logger, diff, **kwargs,
):
    if name != constants.KEYSTONE_ADMIN_SECRET:
        return

    LOG.debug(f"Handling secret create {name}")

    secret_data = {}
    for key in AUTH_KEYS:
        secret_data[key[3:].lower()] = body["data"][key]

    ksadmin_secret = secrets.KeystoneAdminSecret(meta["namespace"])
    ksadmin_secret.save(secret_data)
