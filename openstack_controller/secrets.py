import abc
import base64
from dataclasses import asdict, dataclass
import datetime
import json
from os import urandom
from typing import Dict, List, Optional

import pykube

from cryptography import x509

from cryptography.hazmat.primitives import (
    serialization as crypto_serialization,
)
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import (
    default_backend as crypto_default_backend,
)

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import utils

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

    def __init__(
        self, database=None, messaging=None, notifications=None, memcached=""
    ):
        self.database = database or {}
        self.messaging = messaging or {}
        self.notifications = notifications or {}
        self.memcached = memcached


@dataclass
class BarbicanCredentials(OpenStackCredentials):
    kek: str

    def __init__(
        self,
        database=None,
        messaging=None,
        notifications=None,
        memcached="",
        kek="",
    ):
        super().__init__(database, messaging, notifications, memcached)
        self.kek = kek


@dataclass
class HorizonCredentials(OpenStackCredentials):
    secret_key: str

    def __init__(
        self,
        database=None,
        messaging=None,
        notifications=None,
        memcached="",
        secret_key="",
    ):
        super().__init__(database, messaging, notifications, memcached)
        self.secret_key = secret_key


@dataclass
class NeutronCredentials(OpenStackCredentials):
    metadata_secret: str

    def __init__(
        self,
        database=None,
        messaging=None,
        notifications=None,
        memcached="",
        metadata_secret="",
    ):
        super().__init__(database, messaging, notifications, memcached)
        self.metadata_secret = metadata_secret


@dataclass
class GaleraCredentials:
    sst: OSSytemCreds
    exporter: OSSytemCreds
    audit: OSSytemCreds
    # Backup field is optional till PRODX-6506
    # is fixed properly
    backup: Optional[OSSytemCreds] = None


@dataclass
class RedisCredentials:
    password: str


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
class SignedCertificate:
    cert: str
    key: str
    cert_all: str


@dataclass
class KeycloackCreds:
    passphrase: str


def get_secret_data(namespace: str, name: str):
    secret = kube.find(pykube.Secret, name, namespace)
    return secret.obj["data"]


def generate_password(length: int = 32):
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


# TODO(pas-ha) openstack-helm doesn't support password update by design,
# we will need to get back here when it is solved.


class Secret(abc.ABC):
    secret_name = None
    secret_class = None

    def __init__(self, namespace: str):
        self.namespace = namespace

    def _generate_credentials(
        self, prefix: str, username_length: int = 16, password_length: int = 32
    ) -> OSSytemCreds:
        password = generate_password(length=password_length)
        username = generate_name(prefix=prefix, length=username_length)
        return OSSytemCreds(username=username, password=password)

    @abc.abstractmethod
    def create(self):
        pass

    def decode(self, data):
        params = {}
        for kind, creds in data.items():
            decoded = json.loads(base64.b64decode(creds))
            params[kind] = OSSytemCreds(**decoded)

        return self.secret_class(**params)

    def ensure(self):
        try:
            secret = self.get()
        except pykube.exceptions.ObjectDoesNotExist:
            secret = self.create()
            if secret:
                self.save(secret)
        return secret

    def save(self, secret) -> None:
        data = asdict(secret)

        for key in data.keys():
            data[key] = base64.b64encode(
                json.dumps(data[key]).encode()
            ).decode()

        kube.save_secret_data(self.namespace, self.secret_name, data)

    def get(self):
        data = get_secret_data(self.namespace, self.secret_name)
        return self.decode(data)


class OpenStackAdminSecret(Secret):
    secret_name = constants.ADMIN_SECRET_NAME
    secret_class = OpenStackAdminCredentials

    def create(self) -> OpenStackAdminCredentials:
        db = OSSytemCreds(username="root", password=generate_password())
        messaging = OSSytemCreds(
            username="rabbitmq", password=generate_password()
        )
        identity = OSSytemCreds(username="admin", password=generate_password())

        admin_creds = OpenStackAdminCredentials(
            database=db, messaging=messaging, identity=identity
        )
        return admin_creds


class OpenStackServiceSecret(Secret):
    secret_class = OpenStackCredentials

    def __init__(self, namespace: str, service: str):
        super().__init__(namespace)
        self.secret_name = f"generated-{service}-passwords"
        self.service = service

    def decode(self, data):
        os_creds = self.secret_class()

        for kind, creds in data.items():
            decoded = json.loads(base64.b64decode(creds))
            if kind not in ["database", "messaging", "identity"]:
                setattr(os_creds, kind, decoded)
                continue
            cr = getattr(os_creds, kind)
            for account, c in decoded.items():
                cr[account] = OSSytemCreds(
                    username=c["username"], password=c["password"]
                )

        return os_creds

    def create(self) -> Optional[OpenStackCredentials]:
        os_creds = self.secret_class()
        srv = constants.OS_SERVICES_MAP.get(self.service)
        if srv:
            for service_type in ["database", "messaging", "notifications"]:
                getattr(os_creds, service_type)[
                    "user"
                ] = self._generate_credentials(srv)
            os_creds.memcached = generate_password(length=16)
            return os_creds
        return


class BarbicanSecret(OpenStackServiceSecret):
    secret_class = BarbicanCredentials

    def create(self):
        os_creds = super().create()
        # the kek should be a 32-byte value which is base64 encoded
        os_creds.kek = base64.b64encode(
            generate_password(length=32).encode()
        ).decode()
        return os_creds


class HorizonSecret(OpenStackServiceSecret):
    secret_class = HorizonCredentials

    def create(self):
        os_creds = super().create()
        os_creds.secret_key = generate_password(length=32)
        return os_creds


class NeutronSecret(OpenStackServiceSecret):
    secret_class = NeutronCredentials

    def create(self):
        os_creds = super().create()
        os_creds.metadata_secret = generate_password(length=32)
        return os_creds


class GaleraSecret(Secret):
    secret_name = "generated-galera-passwords"
    secret_class = GaleraCredentials

    def create(self) -> GaleraCredentials:
        return GaleraCredentials(
            sst=self._generate_credentials("sst", 3),
            exporter=self._generate_credentials("exporter", 8),
            audit=self._generate_credentials("audit", 8),
            backup=self._generate_credentials("backup", 8),
        )

    def ensure(self):
        try:
            secret = self.get()
            # To avoid breaking updates backup field will be ensured here
            # till PRODX-6506 is fixed properly
            if not getattr(secret, "backup"):
                backup_creds = self._generate_credentials("backup", 8)
                setattr(secret, "backup", backup_creds)
                self.save(secret)
        except pykube.exceptions.ObjectDoesNotExist:
            secret = self.create()
            if secret:
                self.save(secret)
        return secret


class RedisSecret(Secret):
    secret_name = "generated-redis-password"
    secret_class = RedisCredentials

    def create(self) -> RedisCredentials:
        return RedisCredentials(password=generate_password(length=32))

    def decode(self, data):
        params = {}
        for kind, creds in data.items():
            decoded = base64.b64decode(creds)
            params[kind] = decoded

        return self.secret_class(**params)

    def save(self, secret) -> None:
        data = asdict(secret)

        for key in data.keys():
            data[key] = base64.b64encode(data[key].encode("ascii")).decode()

        kube.save_secret_data(self.namespace, self.secret_name, data)


class PowerDNSSecret(Secret):
    secret_name = "generated-powerdns-passwords"
    secret_class = PowerDnsCredentials

    def decode(self, data):
        data["api_key"] = base64.b64decode(data["api_key"]).decode()
        data["database"] = json.loads(
            base64.b64decode(data["database"]).decode()
        )
        return self.secret_class(
            api_key=data["api_key"], database=OSSytemCreds(**data["database"])
        )

    def create(self):
        return PowerDnsCredentials(
            database=self._generate_credentials("powerdns"),
            api_key=generate_password(length=16),
        )


class SSHSecret(Secret):
    secret_class = SshKey

    def __init__(self, namespace, service, key_size=2048):
        super().__init__(namespace)
        self.secret_name = f"generated-{service}-ssh-creds"
        self.key_size = key_size

    def decode(self, data):
        params = {}
        for kind, creds in data.items():
            decoded = json.loads(base64.b64decode(creds))
            params[kind] = decoded

        return self.secret_class(**params)

    def create(self):
        key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=self.key_size,
        )
        private_key = key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.PKCS8,
            crypto_serialization.NoEncryption(),
        )
        public_key = key.public_key().public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH,
        )
        return SshKey(public=public_key.decode(), private=private_key.decode())


class NgsSSHSecret:
    def __init__(self, namespace):
        self.namespace = namespace
        self.secret_name = f"ngs-ssh-keys"

    def save(self, secret) -> None:
        for key in secret.keys():
            secret[key] = base64.b64encode(secret[key].encode()).decode()

        kube.save_secret_data(self.namespace, self.secret_name, secret)


class SignedCertificateSecret(Secret):
    secret_class = SignedCertificate

    def __init__(self, namespace, service):
        super().__init__(namespace)
        self.secret_name = f"{service}-certs"

    def decode(self, data):
        return self.secret_class(**data)

    def save(self, secret):
        data = asdict(secret)
        for kind, key in data.items():
            if not isinstance(key, bytes):
                key = key.encode()
            data[kind] = base64.b64encode(key).decode()
        kube.save_secret_data(self.namespace, self.secret_name, data)

    def create(self):
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=crypto_default_backend(),
        )
        builder = x509.CertificateBuilder()

        issuer = x509.Name(
            [
                x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(
                    x509.oid.NameOID.STATE_OR_PROVINCE_NAME, "CA"
                ),
                x509.NameAttribute(
                    x509.oid.NameOID.LOCALITY_NAME, "San Francisco"
                ),
                x509.NameAttribute(
                    x509.oid.NameOID.ORGANIZATION_NAME, "Mirantis Inc"
                ),
                x509.NameAttribute(
                    x509.oid.NameOID.COMMON_NAME, "octavia-amphora-ca"
                ),
            ]
        )
        builder = (
            builder.issuer_name(issuer)
            .subject_name(issuer)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            )
            .public_key(key.public_key())
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None), critical=True
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    data_encipherment=True,
                    key_agreement=False,
                    content_commitment=False,
                    key_cert_sign=True,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                        x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    ]
                ),
                critical=True,
            )
        )

        certificate = builder.sign(
            private_key=key,
            algorithm=hashes.SHA256(),
            backend=crypto_default_backend(),
        )
        client_cert = certificate.public_bytes(
            crypto_serialization.Encoding.PEM
        )
        client_key = key.private_bytes(
            encoding=crypto_serialization.Encoding.PEM,
            format=crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=crypto_serialization.NoEncryption(),
        )

        data = {
            "cert": client_cert,
            "key": client_key,
            "cert_all": client_cert + client_key,
        }
        return SignedCertificate(**data)


class KeycloakSecret(Secret):
    secret_name = "oidc-crypto-passphrase"
    secret_class = KeycloackCreds

    def decode(self, data):
        data["passphrase"] = json.loads(
            base64.b64decode(data["passphrase"]).decode()
        )
        return self.secret_class(**data)

    def create(self):
        salt = generate_password()
        return KeycloackCreds(passphrase=salt)


# Ideally, this should be an abstract class as there is no secret_name
class SecretCopy(Secret):
    """Copies secret from namespace to namespace as is"""

    def save(self, secret) -> None:
        kube.save_secret_data(self.namespace, self.secret_name, secret)

    def create(self):
        pass


class TungstenFabricSecret(SecretCopy):
    secret_name = constants.OPENSTACK_TF_SECRET

    def __init__(self, namespace=constants.OPENSTACK_TF_SHARED_NAMESPACE):
        super().__init__(namespace)


class StackLightSecret(SecretCopy):
    secret_name = constants.OPENSTACK_STACKLIGHT_SECRET

    def __init__(
        self, namespace=constants.OPENSTACK_STACKLIGHT_SHARED_NAMESPACE
    ):
        super().__init__(namespace)


class KeystoneAdminSecret(SecretCopy):
    secret_name = constants.KEYSTONE_ADMIN_SECRET


# NOTE(e0ne): Service accounts is a special case so we don't inherit it from
# Secret class now.
class ServiceAccountsSecrets:
    def __init__(
        self,
        namespace: str,
        service: str,
        service_accounts: List[str],
        required_accounts: Dict[str, List[str]],
    ):
        self.namespace = namespace
        self.service = service
        self.service_accounts = service_accounts
        self.required_accounts = required_accounts

    def ensure(self):
        try:
            service_creds = self.get_service_secrets(self.service)
        except pykube.exceptions.ObjectDoesNotExist:
            service_creds = []
            for account in self.service_accounts:
                service_creds.append(
                    OSServiceCreds(
                        account=account,
                        username=generate_name(account),
                        password=generate_password(),
                    )
                )
            self.save_service_secrets(service_creds)

        for service_dep, accounts in self.required_accounts.items():
            secret_name = f"{service_dep}-service-accounts"
            kube.wait_for_secret(self.namespace, secret_name)
            ra_creds = self.get_service_secrets(service_dep)

            for creds in ra_creds:
                if creds.account in accounts:
                    service_creds.append(creds)
        return service_creds

    def get_service_secrets(self, service) -> List[OSServiceCreds]:
        service_creds = []
        data = get_secret_data(self.namespace, f"{service}-service-accounts")
        dict_list = json.loads(base64.b64decode(data[service]))

        for creds in dict_list:
            service_creds.append(OSServiceCreds(**creds))

        return service_creds

    def save_service_secrets(self, credentials: List[OSServiceCreds]) -> None:
        data = []
        for creds in credentials:
            data.append(asdict(creds))
        kube.save_secret_data(
            self.namespace,
            f"{self.service}-service-accounts",
            {
                self.service: base64.b64encode(
                    json.dumps(data).encode()
                ).decode()
            },
        )
