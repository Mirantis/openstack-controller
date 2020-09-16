from unittest import mock
import logging

from openstack_controller import settings


logging.basicConfig(level=logging.DEBUG)

# during layers import k8s config is parsed so a quick fix to avoid fail without config
# TODO(avolkov): make possibility to manage API client creation for tests
mock.patch("pykube.KubeConfig").start()
mock.patch("pykube.HTTPClient").start()


CREDS_KWARGS = {
    "ssh_credentials": {"private": "", "public": ""},
    "credentials": {
        "memcached": "",
        "database": {"user": {"username": "", "password": ""}},
        "messaging": {"user": {"username": "", "password": ""}},
        "notifications": {"user": {"username": "", "password": ""}},
    },
    "admin_creds": {
        "database": {"username": "", "password": ""},
        "identity": {"password": "", "username": ""},
        "messaging": {"password": "", "username": ""},
    },
    "ceph": {
        "nova": {"username": "", "secrets": "", "keyring": "", "pools": {}}
    },
}

settings.OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY = 0
settings.OSCTL_HELMBUNDLE_APPLY_DELAY = 0
