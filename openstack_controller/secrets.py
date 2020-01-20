import base64
from dataclasses import asdict, dataclass
import json
from os import urandom
from typing import Dict, List, Optional

from mcp_k8s_lib import utils
import pykube

from openstack_controller import kube

RGW_KEYSTONE_SECRET = "ceph-keystone-user"
LOG = utils.get_logger(__name__)


@dataclass
class OSSytemCreds:
    username: str
    password: str


@dataclass
class OSServiceCreds(OSSytemCreds):
    account: str


@dataclass
class OpenStackCredentials:
    database: Dict[str, OSSytemCreds]
    messaging: Dict[str, OSSytemCreds]
    notifications: Dict[str, OSSytemCreds]
    memcached: str


@dataclass
class GaleraCredentials:
    sst: OSSytemCreds
    exporter: OSSytemCreds


@dataclass
class PowerDnsCredentials:
    api_key: str
    database: OSSytemCreds


@dataclass
class OpenStackAdminCredentials:
    database: Optional[OSSytemCreds]
    messaging: Optional[OSSytemCreds]
    identity: Optional[OSSytemCreds]


@dataclass
class SshKey:
    public: str
    private: str


@dataclass
class SingedCertificate:
    cert: str
    key: str
    cert_all: str


# TODO(pas-ha) opentack-helm doesn't support password update by design,
# we will need to get back here when it is solved.


def get_powerdns_secret(name: str, namespace: str) -> PowerDnsCredentials:
    data = get_secret_data(namespace, name)
    for kind, creds in data.items():
        data[kind] = json.loads(base64.b64decode(creds))
    return PowerDnsCredentials(
        api_key=data["api_key"],
        database=OSSytemCreds(
            username=data["database"]["username"],
            password=data["database"]["password"],
        ),
    )


def save_powerdns_secret(
    name: str, namespace: str, params: PowerDnsCredentials
):
    data = asdict(params)

    for key in data.keys():
        data[key] = base64.b64encode(json.dumps(data[key]).encode()).decode()

    kube.save_secret_data(namespace, name, data)


def get_galera_secret(name: str, namespace: str) -> GaleraCredentials:
    data = get_secret_data(namespace, name)
    for kind, creds in data.items():
        data[kind] = json.loads(base64.b64decode(creds))
    return GaleraCredentials(
        sst=OSSytemCreds(
            username=data["sst"]["username"], password=data["sst"]["password"]
        ),
        exporter=OSSytemCreds(
            username=data["exporter"]["username"],
            password=data["exporter"]["password"],
        ),
    )


def save_galera_secret(name: str, namespace: str, params: GaleraCredentials):
    data = asdict(params)

    for key in data.keys():
        data[key] = base64.b64encode(json.dumps(data[key]).encode()).decode()

    kube.save_secret_data(namespace, name, data)


def get_ssh_secret(name: str, namespace: str) -> SshKey:
    data = get_secret_data(namespace, name)
    obj = {}
    for kind, key in data.items():
        key_dec = base64.b64decode(key.encode()).decode()
        obj[kind] = key_dec
    return SshKey(**obj)


def save_ssh_secret(name: str, namespace: str, params: SshKey):
    data = asdict(params)
    for kind, key in data.items():
        data[kind] = base64.b64encode(key.encode()).decode()
    kube.save_secret_data(namespace, name, data)


def save_cert_secret(name: str, namespace: str, params: SingedCertificate):
    data = asdict(params)
    for kind, key in data.items():
        if not isinstance(key, bytes):
            key = key.encode()
        data[kind] = base64.b64encode(key).decode()
    kube.save_secret_data(namespace, name, data)


def get_secret_data(namespace: str, name: str):
    secret = kube.find(pykube.Secret, name, namespace)
    return secret.obj["data"]


def get_os_service_secret(
    name: str, namespace: str
) -> Optional[OpenStackCredentials]:
    # pykube.exceptions.ObjectDoesNotExist will be handled on the layer above
    data = get_secret_data(namespace, name)

    os_creds = OpenStackCredentials(
        database={}, messaging={}, notifications={}, memcached=""
    )

    for kind, creds in data.items():
        decoded = json.loads(base64.b64decode(creds))
        if kind == "memcached":
            os_creds.memcached = decoded
            continue
        cr = getattr(os_creds, kind)
        for account, c in decoded.items():

            cr[account] = OSSytemCreds(
                username=c["username"], password=c["password"]
            )

    return os_creds


def get_os_admin_secret(
    name: str, namespace: str
) -> OpenStackAdminCredentials:
    # pykube.exceptions.ObjectDoesNotExist will be handled on the layer above
    secret = kube.find(pykube.Secret, name, namespace)
    data = secret.obj["data"]

    os_creds = OpenStackAdminCredentials(
        database=None, messaging=None, identity=None
    )

    for kind, creds in data.items():
        decoded = json.loads(base64.b64decode(creds))
        setattr(
            os_creds,
            kind,
            OSSytemCreds(
                username=decoded["username"], password=decoded["password"]
            ),
        )

    return os_creds


def save_os_service_secret(
    name: str, namespace: str, params: OpenStackCredentials
):
    data = asdict(params)

    for key in data.keys():
        data[key] = base64.b64encode(json.dumps(data[key]).encode()).decode()

    kube.save_secret_data(namespace, name, data)


def save_os_admin_secret(
    name: str, namespace: str, params: OpenStackAdminCredentials
):
    data = asdict(params)

    for key in data.keys():
        data[key] = base64.b64encode(json.dumps(data[key]).encode()).decode()

    kube.save_secret_data(namespace, name, data)


def generate_password(length=32):
    """
    Generate password of defined length

    Example:
        Output
        ------
        Jda0HK9rM4UETFzZllDPbu8i2szzKbMM
    """
    chars = "aAbBcCdDeEfFgGhHiIjJkKlLmMnNpPqQrRsStTuUvVwWxXyYzZ1234567890"

    return "".join(chars[c % len(chars)] for c in urandom(length))


def generate_name(prefix="", length=16):
    """
    Generate name of defined length

    Example:

        Template
        -------
        {{ generate_name('nova') }}

        Output
        ------
        novaS4LRMYrkh7Nl
    """
    res = [prefix]
    res.append(
        generate_password(
            len(prefix) if length >= len(prefix) else len(prefix) - length
        )
    )
    return "".join(res)


def get_or_create_keycloak_salt(namespace: str, name: str) -> str:
    try:
        data = get_secret_data(namespace, name)
        return base64.b64decode(data["name"])
    except pykube.exceptions.ObjectDoesNotExist:
        salt = generate_password()
        data = {name: base64.b64encode(json.dumps(salt).encode()).decode()}
        kube.save_secret_data(namespace, name, data)
        return data[name]


def get_or_create_service_credentials(
    namespace: str,
    service: str,
    service_accounts: List[str],
    required_accounts: Dict[str, List[str]],
) -> List[OSServiceCreds]:
    try:
        service_creds = get_service_secrets(namespace, service)
    except pykube.exceptions.ObjectDoesNotExist:
        service_creds = []
        for account in service_accounts:
            service_creds.append(
                OSServiceCreds(
                    account=account,
                    username=generate_name(account),
                    password=generate_password(),
                )
            )
        save_service_secrets(namespace, service, service_creds)

    for service_dep, accounts in required_accounts.items():
        secret_name = f"{service_dep}-service-accounts"
        kube.wait_for_secret(namespace, secret_name)
        ra_creds = get_service_secrets(namespace, service_dep)

        for creds in ra_creds:
            if creds.account in accounts:
                service_creds.append(creds)
    return service_creds


def get_service_secrets(namespace: str, service: str) -> List[OSServiceCreds]:
    service_creds = []
    data = get_secret_data(namespace, f"{service}-service-accounts")
    dict_list = json.loads(base64.b64decode(data[service]))

    for creds in dict_list:
        service_creds.append(OSServiceCreds(**creds))

    return service_creds


def save_service_secrets(
    namespace: str, service: str, credentials: List[OSServiceCreds]
) -> None:
    data = []
    for creds in credentials:
        data.append(asdict(creds))
    kube.save_secret_data(
        namespace,
        f"{service}-service-accounts",
        {service: base64.b64encode(json.dumps(data).encode()).decode()},
    )
