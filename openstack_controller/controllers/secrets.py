import base64
import configparser
import json
import kopf
import pykube
import hashlib
import yaml
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
    config = configparser.ConfigParser(strict=False)
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
    labels={"application": "frr"},
)
@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "frr"},
)
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
        },
        subresource="status",
    )


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
    config = configparser.ConfigParser(strict=False)
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
async def handle_rabbitmq_external_secret(
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

    osdpl = kube.get_osdpl(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)
    if (
        not osdpl.obj.get("spec", {})
        .get("features", {})
        .get("messaging", {})
        .get("notifications", {})
        .get("external", {})
        .get("enabled", False)
    ):
        return

    LOG.debug(f"Handling secret create {name}")
    LOG.info(f"The secret {name} changes are: {diff}")

    secret_data = json.loads(
        base64.b64decode(body["data"]["RABBITMQ_USERS"]).decode()
    )

    kube.wait_for_service(
        meta["namespace"], constants.RABBITMQ_EXTERNAL_SERVICE
    )
    rabbitmq_external_service = kube.find(
        pykube.Service,
        constants.RABBITMQ_EXTERNAL_SERVICE,
        meta["namespace"],
    )

    try:
        rabbitmq_external_ingress = rabbitmq_external_service.obj["status"][
            "loadBalancer"
        ]["ingress"]
    except KeyError:
        raise kopf.TemporaryError(
            f"Service {constants.RABBITMQ_EXTERNAL_SERVICE} doesn't have ingress status data"
        )

    rabbitmq_external_ip = None
    for tpl in rabbitmq_external_ingress:
        for key in tpl:
            if key == "ip":
                rabbitmq_external_ip = tpl[key]
    if not rabbitmq_external_ip:
        raise kopf.TemporaryError(
            f"Service {constants.RABBITMQ_EXTERNAL_SERVICE} doesn't have load balancer external IP"
        )

    external_secret_data = {
        "hosts": rabbitmq_external_ip,
        "vhost": "openstack",
    }

    try:
        rabbitmq_external_ports = rabbitmq_external_service.obj["spec"][
            "ports"
        ]
    except KeyError:
        raise kopf.TemporaryError(
            f"Service {constants.RABBITMQ_EXTERNAL_SERVICE} doesn't have ingress status data"
        )

    for port in rabbitmq_external_ports:
        external_secret_data[f'port_{port["name"]}'] = str(port["port"])

    external_secret_data_enc = {
        key: base64.b64encode(value.encode()).decode()
        for key, value in external_secret_data.items()
    }

    # share client-side TLS certificates
    external_certificates_secret = kube.find(
        pykube.Secret,
        constants.RABBITMQ_EXTERNAL_CERTIFICATES_SECRET,
        meta["namespace"],
    )
    external_secret_data_enc.update(
        {
            key: external_certificates_secret.obj["data"][key]
            for key in ("ca_cert", "client_cert", "client_key")
        }
    )

    external_topics = (
        osdpl.obj.get("spec", {})
        .get("features", {})
        .get("messaging", {})
        .get("notifications", {})
        .get("external", {})
        .get("topics", [])
    )
    for topic in external_topics:
        if f"{topic}_external_notifications" not in secret_data:
            LOG.debug(f"The {topic} data is not present in secret.")
            continue

        credentials = {
            key: base64.b64encode(value.encode()).decode()
            for key, value in secret_data[f"{topic}_external_notifications"][
                "auth"
            ][topic].items()
        }

        name = utils.get_topic_normalized_name(topic)
        ets = secrets.ExternalTopicSecret(name)
        ets.save({**credentials, **external_secret_data_enc})


@kopf.on.update(
    "",
    "v1",
    "secrets",
    labels={constants.OSCTL_SECRET_LABEL[0]: constants.OSCTL_SECRET_LABEL[1]},
)
@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={constants.OSCTL_SECRET_LABEL[0]: constants.OSCTL_SECRET_LABEL[1]},
)
async def handle_substitution_secrets(
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):
    LOG.debug(f"Handling secret create/update {name}")
    osdpl = kube.get_osdpl(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)
    if not osdpl:
        return

    hasher = hashlib.sha256()
    hasher.update(json.dumps(body["data"], sort_keys=True).encode())
    secret_hash = hasher.hexdigest()

    osdpl.patch(
        {
            "status": {
                "watched": {
                    "value_from": {"secret": {name: {"hash": secret_hash}}}
                }
            }
        },
        subresource="status",
    )


@kopf.on.update(
    "",
    "v1",
    "secrets",
    labels={"application": "keystone", "component": "os-clouds"},
)
@kopf.on.create(
    "",
    "v1",
    "secrets",
    labels={"application": "keystone", "component": "os-clouds"},
)
async def handle_keystone_osclouds_secret(
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):
    if name != constants.KEYSTONE_OSCLOUDS_SECRET:
        return

    LOG.debug(f"Handling secret create/update {name}")
    osdpl = kube.get_osdpl(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)
    public_domain_name = osdpl.obj["spec"]["public_domain_name"]
    public_auth_url = f"https://keystone.{public_domain_name}/"

    data = yaml.safe_load(
        base64.b64decode(body["data"]["clouds.yaml"]).decode()
    )

    ext_data = {"clouds": {}}
    for context in ["admin", "admin-system"]:
        # keystone-os-clouds secret contains internal endpoints data,
        # so need to convert to public
        data["clouds"][context]["auth"]["auth_url"] = public_auth_url
        data["clouds"][context]["interface"] = "public"
        data["clouds"][context]["endpoint_type"] = "public"
        ext_data["clouds"][context] = data["clouds"][context]

    encoded_ext_data = {
        "clouds.yaml": base64.b64encode(
            yaml.safe_dump(ext_data).encode()
        ).decode()
    }

    secrets.ExternalCredentialSecret("identity").save(encoded_ext_data)

    os_clouds_secret = secrets.OpenStackControllerOSCloudsSecret()
    os_clouds_secret.save(encoded_ext_data)
