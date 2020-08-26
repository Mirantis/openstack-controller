import base64
import configparser
import json
import kopf
import pykube
from urllib.parse import urlsplit

from openstack_controller import ceph_api
from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import secrets
from openstack_controller import settings  # noqa
from openstack_controller import utils

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
@utils.collect_handler_metrics
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


@kopf.on.resume(
    "",
    "v1",
    "secrets",
    labels={"application": "neutron", "component": "server"},
)
@kopf.on.update(
    "",
    "v1",
    "secrets",
    labels={"application": "neutron", "component": "server"},
)
@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "neutron", "component": "server"},
)
@utils.collect_handler_metrics
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


@kopf.on.resume(
    "",
    "v1",
    "secrets",
    labels={"application": "neutron", "component": "configmap_etc"},
)
@kopf.on.update(
    "",
    "v1",
    "secrets",
    labels={"application": "neutron", "component": "configmap_etc"},
)
@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "neutron", "component": "configmap_etc"},
)
@utils.collect_handler_metrics
async def handle_neutron_configmap_secret(
    body, meta, name, status, logger, diff, **kwargs,
):
    METADATA_OPTS = (
        ("nova_metadata_port", "nova_metadata_port"),
        ("nova_metadata_host", "nova_metadata_host"),
        ("metadata_proxy_secret", "metadata_proxy_shared_secret"),
    )

    LOG.debug(f"Handling secret create {name}")
    metadata = base64.b64decode(body["data"]["metadata_agent.ini"]).decode()
    config = configparser.ConfigParser()
    config.read_string(metadata)

    secret_data = {
        key: base64.b64encode(config["DEFAULT"][opt].encode()).decode()
        for key, opt in METADATA_OPTS
    }
    tfs = secrets.TungstenFabricSecret()
    tfs.save(secret_data)


@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "keystone", "component": "server"},
)
@utils.collect_handler_metrics
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


@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "rabbitmq", "component": "server"},
)
@utils.collect_handler_metrics
async def handle_rabbitmq_secret(
    body, meta, name, status, logger, diff, **kwargs,
):
    if name != constants.RABBITMQ_USERS_CREDENTIALS_SECRET:
        return

    LOG.debug(f"Handling secret create {name}")

    credentials = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in json.loads(
            base64.b64decode(body["data"]["RABBITMQ_USERS"]).decode()
        )["stacklight_service_notifications"]["auth"]["stacklight"].items()
    }

    kube.wait_for_secret(meta["namespace"], constants.KEYSTONE_CONFIG_SECRET)
    keystone_config_secret = kube.find(
        pykube.Secret, constants.KEYSTONE_CONFIG_SECRET, meta["namespace"]
    )
    keystone_conf = base64.b64decode(
        keystone_config_secret.obj["data"]["keystone.conf"]
    ).decode()
    config = configparser.ConfigParser()
    config.read_string(keystone_conf)

    transport_url = urlsplit(
        config["oslo_messaging_notifications"]["transport_url"]
    )
    location_path = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in {
            "hosts": json.dumps(
                [
                    host.split("@")[1]
                    for host in transport_url.netloc.split(",")
                ]
            ),
            "vhost": transport_url.path,
        }.items()
    }

    sls = secrets.StackLightSecret()
    sls.save({**credentials, **location_path})
