import enum
import sys


TRUE_STRINGS = {"1", "t", "true", "on", "y", "yes"}
FALSE_STRINGS = {"0", "f", "false", "off", "n", "no"}

ADMIN_SECRET_NAME = "openstack-admin-users"

CACHE_NAME = "image-precaching"

CHART_GROUP_MAPPING = {
    "openstack": [
        "cinder",
        "glance",
        "heat",
        "horizon",
        "ironic",
        "keystone",
        "neutron",
        "nova",
        "octavia",
        "designate",
        "barbican",
        "placement",
        "tempest",
        "stepler",
        "aodh",
        "panko",
        "ceilometer",
        "masakari",
    ],
    "infra": [
        "rabbitmq",
        "mariadb",
        "memcached",
        "openvswitch",
        "libvirt",
        "ingress",
        "etcd",
        "descheduler",
        "gnocchi",
        "ceph-rgw",
        "frr",
        "iscsi",
        "strongswan",
    ],
}

OS_SERVICES_MAP = {
    "block-storage": "cinder",
    "compute": "nova",
    "dns": "designate",
    "identity": "keystone",
    "image": "glance",
    "networking": "neutron",
    "orchestration": "heat",
    "dashboard": "horizon",
    "load-balancer": "octavia",
    "key-manager": "barbican",
    "placement": "placement",
    "baremetal": "ironic",
    "alarming": "aodh",
    "event": "panko",
    "metering": "ceilometer",
    "metric": "gnocchi",
    "tempest": "tempest",
    "object-storage": "ceph-rgw",
    "instance-ha": "masakari",
}

OS_POLICY_SERVICES = {
    "block-storage": "cinder",
    "compute": "nova",
    "dns": "designate",
    "identity": "keystone",
    "image": "glance",
    "networking": "neutron",
    "orchestration": "heat",
    "load-balancer": "octavia",
    "key-manager": "barbican",
    "placement": "placement",
    "baremetal": "ironic",
    "alarming": "aodh",
    "event": "panko",
    "metric": "gnocchi",
    "instance-ha": "masakari",
}

OPENSTACK_SERVICES_UPGRADE_ORDER = [
    "identity",
    "placement",
    "image",
    "networking",
    "compute",
    "block-storage",
    "load-balancer",
    "dns",
    "key-manager",
    "orchestration",
    "dashboard",
    "object-storage",
    "instance-ha",
]

RGW_KEYSTONE_SECRET = "ceph-keystone-user"

# Health
UNKNOWN, OK, PROGRESS, BAD = "Unknown", "Ready", "Progressing", "Unhealthy"

NEUTRON_KEYSTONE_SECRET = "neutron-keystone-admin"
KEYSTONE_ADMIN_SECRET = "keystone-keystone-admin"
KEYSTONE_CONFIG_SECRET = "keystone-etc"
RABBITMQ_USERS_CREDENTIALS_SECRET = "openstack-rabbitmq-users-credentials"
OPENSTACK_TF_SHARED_NAMESPACE = "openstack-tf-shared"
OPENSTACK_TF_SECRET = "tf-data"
TF_OPENSTACK_SECRET = "ost-data"
OPENSTACK_STACKLIGHT_SHARED_NAMESPACE = "openstack-lma-shared"
OPENSTACK_STACKLIGHT_SECRET = "rabbitmq-creds"
OPENSTACK_IAM_SECRET = "openstack-iam-shared"

COMPUTE_NODE_CONTROLLER_SECRET_NAME = "keystone-os-clouds"


class OpenStackVersion(enum.IntEnum):
    """Ordered OpenStack version"""

    queens = 1
    rocky = 2
    stein = 3
    train = 4
    ussuri = 5
    victoria = 6
    wallaby = 7
    xena = 8
    yoga = 9
    master = sys.maxsize


# Enum for supported OpenStack-related node roles
class NodeRole(enum.Enum):
    compute = "compute"
    gateway = "gateway"
    controller = "controller"


POLICY_IN_CODE_SERVICES = [
    "keystone",
    "glance",
    "cinder",
    "nova",
    "designate",
    "neutron",
    "heat",
    "octavia",
    "barbican",
    "placement",
    "ironic",
    "aodh",
    "gnocchi",
    "masakari",
]
