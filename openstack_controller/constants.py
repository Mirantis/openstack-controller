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
        "designate",
        "barbican",
        "placement",
        "tempest",
        "stepler",
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
        "ceph-rgw",
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

COMPUTE_NODE_CONTROLLER_SECRET_NAME = "nova-keystone-admin"


class OpenStackVersion(enum.IntEnum):
    """Ordered OpenStack version"""

    queens = 1
    rocky = 2
    stein = 3
    train = 4
    ussuri = 5
    victoria = 6
    master = sys.maxsize
