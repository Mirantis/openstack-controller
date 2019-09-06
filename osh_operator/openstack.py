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


def _generate_credentials(username: str) -> secrets.OSSytemCreds:
    password = secrets.generate_password()
    return secrets.OSSytemCreds(username=username, password=password)


def get_or_create_os_credentials(service, namespace):
    secret_name = f"generated-{service}-passwords"
    try:
        os_creds = secrets.get_os_service_secret(secret_name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        os_creds = secrets.OpenStackCredentials(
            database={}, messaging={}, notifications={}
        )
        srv = OS_SERVICES_MAP.get(service)
        if srv:
            for service_type in ["database", "messaging", "notifications"]:
                getattr(os_creds, service_type)[
                    "user"
                ] = _generate_credentials(srv)
        else:
            # TODO(e0ne): add logging here
            return

        secrets.save_os_service_secret(secret_name, namespace, os_creds)
    return os_creds
