import enum
import sys


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
        "ceph-rgw",
        "designate",
        "barbican",
        "placement",
        "tempest",
        "dashboard-selenium",
        "aodh",
        "panko",
        "ceilometer",
    ],
    "infra": [
        "rabbitmq",
        "mariadb",
        "memcached",
        "openvswitch",
        "libvirt",
        "ingress",
        "etcd",
        "gnocchi",
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
OPENSTACK_STACKLIGHT_SHARED_NAMESPACE = "openstack-lma-shared"
OPENSTACK_STACKLIGHT_SECRET = "rabbitmq-creds"

COMPUTE_NODE_CONTROLLER_SECRET_NAME = "compute-node-controller-openstack-creds"


class OpenStackVersion(enum.IntEnum):
    """Ordered OpenStack version"""

    queens = 1
    rocky = 2
    stein = 3
    train = 4
    ussuri = 5
    master = sys.maxsize
