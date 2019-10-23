from typing import Optional

import pykube

from . import secrets

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
}

ADMIN_SECRET_NAME = "openstack-admin-users"
GALERA_SECRET_NAME = "generated-galera-passwords"


def _generate_credentials(
    prefix: str, username_length: int = 16, password_length: int = 32
) -> secrets.OSSytemCreds:
    password = secrets.generate_password(length=password_length)
    username = secrets.generate_name(prefix=prefix, length=username_length)
    return secrets.OSSytemCreds(username=username, password=password)


def get_or_create_galera_credentials(
    namespace: str
) -> secrets.GaleraCredentials:
    try:
        galera_creds = secrets.get_galera_secret(GALERA_SECRET_NAME, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        galera_creds = secrets.GaleraCredentials(
            sst=_generate_credentials("sst", 3),
            exporter=_generate_credentials("exporter", 8),
        )
        secrets.save_galera_secret(GALERA_SECRET_NAME, namespace, galera_creds)

    return galera_creds


def get_or_create_os_credentials(
    service: str, namespace: str
) -> Optional[secrets.OpenStackCredentials]:
    secret_name = f"generated-{service}-passwords"
    try:
        os_creds = secrets.get_os_service_secret(secret_name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        os_creds = secrets.OpenStackCredentials(
            database={}, messaging={}, notifications={}, memcached={}
        )
        srv = OS_SERVICES_MAP.get(service)
        if srv:
            for service_type in ["database", "messaging", "notifications"]:
                getattr(os_creds, service_type)[
                    "user"
                ] = _generate_credentials(srv, 16)
            os_creds.memcached = secrets.generate_password(length=16)
        elif service == "powerdns":
            os_creds.database["user"] = _generate_credentials(service, 16)
        else:
            # TODO(e0ne): add logging here
            return

        secrets.save_os_service_secret(secret_name, namespace, os_creds)
    return os_creds


def create_admin_credentials(namespace: str):
    db = secrets.OSSytemCreds(
        username="root", password=secrets.generate_password()
    )
    messaging = secrets.OSSytemCreds(
        username="rabbitmq", password=secrets.generate_password()
    )
    identity = secrets.OSSytemCreds(
        username="admin", password=secrets.generate_password()
    )

    admin_creds = secrets.OpenStackAdminCredentials(
        database=db, messaging=messaging, identity=identity
    )

    secrets.save_os_admin_secret(ADMIN_SECRET_NAME, namespace, admin_creds)


def get_admin_credentials(namespace: str) -> secrets.OpenStackAdminCredentials:
    return secrets.get_os_admin_secret(ADMIN_SECRET_NAME, namespace)


def get_or_create_admin_credentials(
    namespace
) -> secrets.OpenStackAdminCredentials:
    try:
        return get_admin_credentials(namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        return create_admin_credentials(namespace)
