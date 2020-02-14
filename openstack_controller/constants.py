ADMIN_SECRET_NAME = "openstack-admin-users"

CACHE_NAME = "image-precaching"

CHART_GROUP_MAPPING = {
    "openstack": [
        "cinder",
        "glance",
        "heat",
        "horizon",
        "keystone",
        "neutron",
        "nova",
        "octavia",
        "ceph-rgw",
        "designate",
        "barbican",
        "placement",
        "tempest",
    ],
    "infra": [
        "rabbitmq",
        "mariadb",
        "memcached",
        "openvswitch",
        "libvirt",
        "ingress",
        "etcd",
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
}

OPENSTACK_SERVICES_UPGRADE_ORDER = [
    "identity",
    "placement",
    "image",
    "networking",
    "compute",
    "volume",
    "load-balancer",
    "dns",
    "key-manager",
    "orchestration",
    "dashboard",
]

RGW_KEYSTONE_SECRET = "ceph-keystone-user"

# Health
UNKNOWN, OK, PROGRESS, BAD = "Unknown", "Ready", "Progressing", "Unhealthy"
