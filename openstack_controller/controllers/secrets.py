import base64
import configparser
import json
import kopf
import pykube
import hashlib
from urllib.parse import urlsplit

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
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):
    if name != constants.NEUTRON_KEYSTONE_SECRET:
        return

    LOG.debug(f"Handling secret create/update {name}")
    LOG.info(f"The secret {name} changes are: {diff}")

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
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):
    METADATA_OPTS = (
        ("nova_metadata_port", "nova_metadata_port"),
        ("nova_metadata_host", "nova_metadata_host"),
        ("metadata_proxy_secret", "metadata_proxy_shared_secret"),
    )

    LOG.debug(f"Handling secret create {name}")
    LOG.info(f"The secret {name} changes are: {diff}")
    metadata = base64.b64decode(body["data"]["metadata_agent.ini"]).decode()
    config = configparser.ConfigParser()
    config.read_string(metadata)

    secret_data = {
        key: base64.b64encode(config["DEFAULT"][opt].encode()).decode()
        for key, opt in METADATA_OPTS
    }
    tfs = secrets.TungstenFabricSecret()
    tfs.save(secret_data)


# NOTE(vsaienko): we do not need to listen for resume event, as it will trigger
# services update anyway
@kopf.on.update(
    "",
    "v1",
    "secrets",
)
@kopf.on.create(
    "",
    "v1",
    "secrets",
)
@utils.collect_handler_metrics
async def handle_bgpvpnsecret(
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):

    if name != settings.OSCTL_BGPVPN_NEIGHBOR_INFO_SECRET_NAME:
        return
    LOG.info(f"The secret {name} changes are: {diff}")

    osdpl = kube.get_osdpl(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)

    hasher = hashlib.sha256()
    hasher.update(json.dumps(body["data"], sort_keys=True).encode())
    secret_hash = hasher.hexdigest()

    osdpl.patch(
        {
            "status": {
                "watched": {
                    "neutron": {
                        "bgpvpn_neighbor_secret": {"hash": secret_hash}
                    }
                }
            }
        }
    )


@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "keystone", "component": "server"},
)
@utils.collect_handler_metrics
async def handle_keystone_secret(
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):
    if name != constants.KEYSTONE_ADMIN_SECRET:
        return

    LOG.debug(f"Handling secret create {name}")

    secret_data = {}
    for key in AUTH_KEYS:
        secret_data[key[3:].lower()] = body["data"][key]

    ksadmin_secret = secrets.KeystoneAdminSecret(meta["namespace"])
    ksadmin_secret.save(secret_data)


@kopf.on.update(
    "",
    "v1",
    "secrets",
    labels={"application": "rabbitmq", "component": "server"},
)
@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "rabbitmq", "component": "server"},
)
@utils.collect_handler_metrics
async def handle_rabbitmq_secret(
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):
    if name != constants.RABBITMQ_USERS_CREDENTIALS_SECRET:
        return

    LOG.debug(f"Handling secret create {name}")
    LOG.info(f"The secret {name} changes are: {diff}")

    secret_data = json.loads(
        base64.b64decode(body["data"]["RABBITMQ_USERS"]).decode()
    )

    if "stacklight_service_notifications" not in secret_data:
        LOG.debug("The stacklight data is not present in secret.")
        return

    credentials = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in secret_data["stacklight_service_notifications"][
            "auth"
        ]["stacklight"].items()
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
