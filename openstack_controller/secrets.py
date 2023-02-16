import abc
import base64
from dataclasses import asdict, dataclass, fields
import datetime
import json
from os import urandom
from typing import Dict, List, Optional, final

import kopf
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
import marshmallow
import marshmallow_dataclass

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import utils
from openstack_controller import settings

LOG = utils.get_logger(__name__)


@dataclass
class Serializer:
    def to_json(self):
        return asdict(self)

    @classmethod
    def from_json(cls, data):
        schema = marshmallow_dataclass.class_schema(cls)()
        return schema.load(data)


@dataclass
class OSSytemCreds(Serializer):
    username: str
    password: str


@dataclass
class OSServiceCreds(OSSytemCreds):
    account: str


@dataclass
class OpenStackCredentials(Serializer):
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
    ipsec_secret_key: str

    def __init__(
        self,
        database=None,
        messaging=None,
        notifications=None,
        memcached="",
        metadata_secret="",
        ipsec_secret_key="",
    ):
        super().__init__(database, messaging, notifications, memcached)
        self.metadata_secret = metadata_secret
        self.ipsec_secret_key = ipsec_secret_key


@dataclass
class GaleraCredentials(Serializer):
    sst: OSSytemCreds
    exporter: OSSytemCreds
    audit: OSSytemCreds
    backup: OSSytemCreds


@dataclass
class RedisCredentials(Serializer):
    password: str


@dataclass
class PowerDnsCredentials(Serializer):
    api_key: str
    database: OSSytemCreds


@dataclass
class OpenStackAdminCredentials(Serializer):
    database: Optional[OSSytemCreds]
    messaging: Optional[OSSytemCreds]
    identity: Optional[OSSytemCreds]


@dataclass
class RabbitmqGuestCredentials(Serializer):
    password: str


@dataclass
class SshKey(Serializer):
    public: str
    private: str


@dataclass
class SignedCertificate(Serializer):
    cert: str
    key: str
    cert_all: str


@dataclass
class VncSignedCertificate(Serializer):
    ca_cert: str
    ca_key: str
    server_cert: str
    server_key: str
    client_cert: str
    client_key: str


@dataclass
class KeycloackCreds(Serializer):
    passphrase: str


def get_secret(namespace: str, name: str, silent: bool = False):
    secret = kube.find(pykube.Secret, name, namespace, silent=silent)
    return secret


def get_secret_data(namespace: str, name: str):
    secret = get_secret(namespace, name)
    return secret.obj["data"]


def get_secret_priority(secret):
    secret.reload()
    return int(secret.annotations.get(constants.SECRET_PRIORITY, 0))


def set_secret_priority(secret, priority):
    secret.patch(
        {
            "metadata": {
                "annotations": {constants.SECRET_PRIORITY: str(priority)}
            }
        }
    )


def get_secrets_sorted(namespace, names):
    """
    Get secret objects by names and sort them by priority

    Method creates list of found secrets having priority, and sorts it,
    secrets which don't have priority are appended to end of
    the list.

    :param namespace: string name of secrets namespace
    :param names: list of secret names to search and sort

    :returns list of pykube.Secret objects and/or NoneType objects
    """
    res_map = {}
    no_priority = []
    for name in names:
        secret = get_secret(namespace, name, silent=True)
        if secret is not None:
            priority = get_secret_priority(secret)
            if priority != 0:
                res_map[priority] = secret
            else:
                no_priority.append(secret)
    res = []
    for priority in sorted(res_map.keys(), reverse=True):
        res.append(res_map[priority])
    res.extend(no_priority)
    return res


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


def generate_credentials(
    prefix: str, username_length: int = 16, password_length: int = 32
) -> OSSytemCreds:
    password = generate_password(length=password_length)
    username = generate_name(prefix=prefix, length=username_length)
    return OSSytemCreds(username=username, password=password)


class Secret(abc.ABC):
    secret_name = None
    secret_class = None

    def __init__(self, namespace: str):
        self.namespace = namespace

    def _fill_new_fields(self, secret, to_update: dict):
        """
        Create/add/modify fields according to secret format

        The method can modify secret by adding new fields or
        modify existing fields in secret (e.g update password).
        Returns object of self.secret_class - e.g. OpenStackAdminCredentials

        :param secret: Dict
        :param to_update: Dict of next format {"creds_name":["field1", "field2"]}
                          TODO(mkarpin): add ability to work with nested fields
        :returns cls.secret_class instance
        """
        new_dict = self.secret_class.to_json(self.create())
        for creds_name, creds_fields in to_update.items():
            if not creds_fields or creds_name not in secret.keys():
                secret[creds_name] = new_dict[creds_name]
            else:
                for field in creds_fields:
                    secret[creds_name][field] = new_dict[creds_name][field]
        return self.secret_class.from_json(secret)

    @abc.abstractmethod
    def create(self):
        """Initialize secret in cls.secret_class format"""
        pass

    def _update_format(self, data):
        all_fields = [f.name for f in fields(self.secret_class)]
        new_fields = {f: [] for f in set(all_fields) - set(data)}
        return self._fill_new_fields(data, new_fields)

    def ensure(self):
        """Ensure k8s secret exists and is in correct format.

        Make sure k8s representation of cls.secret_class:
          * Exists
          * Is in correct format
        :returns : TODO(vsaienko) should not return anything.
        """
        try:
            secret = self.get()
        except pykube.exceptions.ObjectDoesNotExist:
            secret = self.create()
            if secret:
                self.save(secret)
        except marshmallow.exceptions.ValidationError:
            LOG.info(
                f"Secret {self.secret_name} has incorrect format. Updating it..."
            )
            data = self.get_data()
            secret = self._update_format(data)
            self.save(secret)

        return secret

    @final
    def save(self, secret) -> None:
        """Save cls.secret_class instance to k8s secret"""
        data = self.secret_class.to_json(secret)

        for key in data.keys():
            value = data[key]
            if isinstance(value, dict):
                value = json.dumps(value)
            data[key] = base64.b64encode(value.encode()).decode()
        kube.save_secret_data(self.namespace, self.secret_name, data)

    @final
    def get_data(self):
        """Get data from k8s and return dict"""
        data = {}
        raw_data = get_secret_data(self.namespace, self.secret_name)
        for key in raw_data.keys():
            value = base64.b64decode(raw_data[key]).decode()
            try:
                data[key] = json.loads(value)
            except json.decoder.JSONDecodeError:
                data[key] = value
        return data

    @final
    def get(self):
        """Get data from k8s and return instance of cls.secret_class"""
        data = self.get_data()
        return self.secret_class.from_json(data)


class MultiSecret(abc.ABC):
    secret_base_name = None
    secret_class = None

    def __init__(self, namespace: str):
        self.namespace = namespace
        self._secret_names = [
            self.secret_base_name,
            f"{self.secret_base_name}-1",
        ]

    @property
    def k8s_secrets(self):
        return get_secrets_sorted(self.namespace, self._secret_names)

    def k8s_get_data(self, name):
        for secret in self.k8s_secrets:
            if secret.name == name:
                secret.reload()
                return secret.obj["data"]
        raise pykube.exceptions.ObjectDoesNotExist()

    def _fill_new_fields(self, secret, to_update: dict):
        """
        Create/add/modify fields according to secret format

        The method can modify secret by adding new fields or
        modify existing fields in secret (e.g update password).
        Returns object of self.secret_class - e.g. OpenStackAdminCredentials

        :param secret: Dict
        :param to_update: Dict of next format {"creds_name":["field1", "field2"]}
                          TODO(mkarpin): add ability to work with nested fields
        :returns cls.secret_class instance
        """
        new_dict = self.secret_class.to_json(self.create())
        for creds_name, creds_fields in to_update.items():
            if not creds_fields or creds_name not in secret.keys():
                secret[creds_name] = new_dict[creds_name]
            else:
                for field in creds_fields:
                    secret[creds_name][field] = new_dict[creds_name][field]
        return self.secret_class.from_json(secret)

    @abc.abstractmethod
    def create(self):
        """Initialize secret in cls.secret_class format"""
        pass

    @abc.abstractmethod
    def rotate(self):
        """Rotate/change credentials in secret"""
        pass

    def _update_format(self, data):
        all_fields = [f.name for f in fields(self.secret_class)]
        new_fields = {f: [] for f in set(all_fields) - set(data)}
        return self._fill_new_fields(data, new_fields)

    def ensure(self):
        """Ensure k8s secrets exist and are in correct format.

        Make sure k8s representation of each secret of cls.secret_class:
          * Exist
          * Is in correct format
        :returns : TODO(vsaienko) should not return anything.
        """
        for name in self._secret_names:
            try:
                secret = self.get(name=name)
            except pykube.exceptions.ObjectDoesNotExist:
                secret = self.create()
                if secret:
                    self.save(secret, name)
            except marshmallow.exceptions.ValidationError:
                LOG.info(f"Secret {name} has incorrect format. Updating it...")
                data = self.get_data(name)
                secret = self._update_format(data)
                self.save(secret, name)
        # there are some OpenstackServiceSecret secrets which
        # return None on self.create() e.g memcached
        if secret:
            return self.get()

    @final
    def save(self, secret, name) -> None:
        """Save cls.secret_class instance to k8s secret"""
        data = self.secret_class.to_json(secret)

        for key in data.keys():
            value = data[key]
            if isinstance(value, dict):
                value = json.dumps(value)
            data[key] = base64.b64encode(value.encode()).decode()
        kube.save_secret_data(self.namespace, name, data)

    @final
    def get_data(self, name):
        """Get data from k8s and return dict"""
        data = {}
        raw_data = self.k8s_get_data(name)
        for key in raw_data.keys():
            value = base64.b64decode(raw_data[key]).decode()
            try:
                data[key] = json.loads(value)
            except json.decoder.JSONDecodeError:
                data[key] = value
        return data

    @final
    def get(self, seq=0, name=None):
        """Get data from k8s and return instance of cls.secret_class"""
        if not name:
            name = self.k8s_secrets[seq].name
        data = self.get_data(name)
        return self.secret_class.from_json(data)


class OpenStackAdminSecret(MultiSecret):
    secret_base_name = constants.ADMIN_SECRET_NAME
    secret_class = OpenStackAdminCredentials

    def create(self) -> OpenStackAdminCredentials:
        db = OSSytemCreds(username="root", password=generate_password())
        messaging = OSSytemCreds(
            username="rabbitmq", password=generate_password()
        )
        identity = OSSytemCreds(
            username=generate_name("admin"), password=generate_password()
        )
        admin_creds = OpenStackAdminCredentials(
            database=db, messaging=messaging, identity=identity
        )
        return admin_creds

    def rotate(self, rotation_id):
        active, backup = self.k8s_secrets

        secret_rotation_id = get_secret_priority(active)
        if secret_rotation_id == rotation_id:
            LOG.info(f"Secret {active.name} already is rotated")
            return
        # for case when osdpl object was recreated on environment
        # where rotation has been performed and existing secrets may have
        # rotation_id set to some value
        elif secret_rotation_id > rotation_id:
            raise kopf.TemporaryError(
                f"Cannot rotate, secret {active.name} has greater rotation_id, than requested"
            )

        LOG.info(f"Starting rotation of active secret {active.name}")
        LOG.info(f"Backup secret {backup.name} will be promoted to active")

        active_data = self.get_data(active.name)
        backup_data = self.get_data(backup.name)
        # currently only identity rotation is supported
        # other fields should be copied
        for field in active_data.keys():
            if field != "identity":
                backup_data[field] = active_data[field]
        secret = self._fill_new_fields(backup_data, {"identity": ["password"]})
        self.save(secret, backup.name)
        set_secret_priority(backup, rotation_id)


class RabbitmqGuestSecret(Secret):
    secret_name = "generated-rabbitmq-password"
    secret_class = RabbitmqGuestCredentials

    def create(self) -> RabbitmqGuestCredentials:
        return RabbitmqGuestCredentials(password=generate_password())


class OpenStackServiceSecret(Secret):
    secret_class = OpenStackCredentials

    def __init__(self, namespace: str, service: str):
        super().__init__(namespace)
        self.secret_name = f"generated-{service}-passwords"
        self.service = service

    def create(self) -> Optional[OpenStackCredentials]:
        os_creds = self.secret_class()
        srv = constants.OS_SERVICES_MAP[self.service]
        for service_type in ["database", "messaging", "notifications"]:
            getattr(os_creds, service_type)["user"] = generate_credentials(srv)
        os_creds.memcached = generate_password(length=16)
        return os_creds


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
        os_creds.ipsec_secret_key = generate_password(length=16)
        return os_creds


class GaleraSecret(Secret):
    secret_name = "generated-galera-passwords"
    secret_class = GaleraCredentials

    def create(self) -> GaleraCredentials:
        return GaleraCredentials(
            sst=generate_credentials("sst", 3),
            exporter=generate_credentials("exporter", 8),
            audit=generate_credentials("audit", 8),
            backup=generate_credentials("backup", 8),
        )


class RedisSecret(Secret):
    secret_name = "generated-redis-password"
    secret_class = RedisCredentials

    def create(self) -> RedisCredentials:
        return RedisCredentials(password=generate_password(length=32))


class StackLightPasswordSecret(Secret):
    secret_name = "generated-stacklight-password"
    secret_class = OSSytemCreds

    def create(self) -> OSSytemCreds:
        return OSSytemCreds(
            password=generate_password(length=32),
            username=generate_name(prefix="stacklight", length=16),
        )


class ExternalTopicPasswordSecret(Secret):
    secret_class = OSSytemCreds

    def __init__(self, namespace: str, topic: str, name: str):
        super().__init__(namespace)
        self.secret_name = f"generated-notifications-{name}-passwords"
        self.topic = topic

    def create(self) -> OSSytemCreds:
        return OSSytemCreds(
            password=generate_password(length=32),
            username=generate_name(prefix=self.topic, length=16),
        )


class PowerDNSSecret(Secret):
    secret_name = "generated-powerdns-passwords"
    secret_class = PowerDnsCredentials

    def create(self):
        return PowerDnsCredentials(
            database=generate_credentials("powerdns"),
            api_key=generate_password(length=16),
        )


class SSHSecret(Secret):
    secret_class = SshKey

    def __init__(self, namespace, service, key_size=2048):
        super().__init__(namespace)
        self.secret_name = f"generated-{service}-ssh-creds"
        self.key_size = key_size

    def create(self):
        key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=self.key_size,
        )
        private_key = key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
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
                datetime.datetime.utcnow() + datetime.timedelta(days=10 * 365)
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
        data = {k: v.decode() for k, v in data.items()}
        return SignedCertificate(**data)


class VncSignedCertificateSecret(Secret):
    secret_class = VncSignedCertificate

    def __init__(self, namespace, service, san_name, cn_name):
        super().__init__(namespace)
        self.secret_name = f"{service}-certs"
        self.san_name = san_name
        self.cn_name = cn_name

    def _generate_cert(self, issuer, ca_cert, ca_key):
        cert_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=crypto_default_backend(),
        )
        new_subject = x509.Name(
            [
                x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, self.cn_name),
            ]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(new_subject)
            .issuer_name(ca_cert.issuer)
            .public_key(cert_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=10 * 365)
            )
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(self.san_name)]),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    content_commitment=False,
                    key_cert_sign=False,
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
            .sign(ca_key, hashes.SHA256(), crypto_default_backend())
        )
        cert_pem = cert.public_bytes(
            encoding=crypto_serialization.Encoding.PEM
        )

        cert_key_pem = cert_key.private_bytes(
            encoding=crypto_serialization.Encoding.PEM,
            format=crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=crypto_serialization.NoEncryption(),
        )

        return {"cert_pem": cert_pem, "cert_key_pem": cert_key_pem}

    def create(self):
        # Generate CA cert
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
                x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "Mirantis"),
            ]
        )
        builder = (
            builder.issuer_name(issuer)
            .subject_name(issuer)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=10 * 365)
            )
            .public_key(key.public_key())
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None), critical=True
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    content_commitment=False,
                    key_cert_sign=True,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
        )

        certificate = builder.sign(
            private_key=key,
            algorithm=hashes.SHA256(),
            backend=crypto_default_backend(),
        )
        ca_cert = certificate.public_bytes(crypto_serialization.Encoding.PEM)
        ca_key = key.private_bytes(
            encoding=crypto_serialization.Encoding.PEM,
            format=crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=crypto_serialization.NoEncryption(),
        )

        root_key = crypto_serialization.load_pem_private_key(
            ca_key, password=None, backend=crypto_default_backend()
        )
        root_cert = x509.load_pem_x509_certificate(
            ca_cert, crypto_default_backend()
        )

        # Generate server sertificates
        server_cert = self._generate_cert(issuer, root_cert, root_key)

        # Generate client sertificates
        client_cert = self._generate_cert(issuer, root_cert, root_key)

        data = {
            "ca_cert": ca_cert,
            "ca_key": ca_key,
            "server_cert": server_cert["cert_pem"],
            "server_key": server_cert["cert_key_pem"],
            "client_cert": client_cert["cert_pem"],
            "client_key": client_cert["cert_key_pem"],
        }
        data = {k: v.decode() for k, v in data.items()}
        return VncSignedCertificate(**data)


class KeycloakSecret(Secret):
    secret_name = "oidc-crypto-passphrase"
    secret_class = KeycloackCreds

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


class ExternalTopicSecret(SecretCopy):
    def __init__(
        self,
        name,
        namespace=constants.OPENSTACK_EXTERNAL_NAMESPACE,
    ):
        super().__init__(namespace)
        self.secret_name = f"openstack-{name}-notifications"


@dataclass
class OpenStackIAMData:
    clientId: str
    redirectUris: List[str]


class IAMSecret:
    secret_name = constants.OPENSTACK_IAM_SECRET

    labels = {"kaas.mirantis.com/openstack-iam-shared": "True"}

    def __init__(self, namespace: str):
        self.namespace = namespace

    def save(self, secret: OpenStackIAMData) -> None:
        data = {"client": asdict(secret)}

        data["client"] = base64.b64encode(
            json.dumps(data["client"]).encode()
        ).decode()

        kube.save_secret_data(
            self.namespace, self.secret_name, data, labels=self.labels
        )


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
        existing_accounts = [x.account for x in service_creds]
        for account in self.service_accounts:
            if account not in existing_accounts:
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


class JsonSecret:
    """The secret where values of keys is in json format"""

    def __init__(self, namespace: str, name: str):
        self.namespace = namespace
        self.name = name
        meta = {"name": self.name, "namespace": self.namespace}
        self.kube_obj = pykube.Secret(kube.api, {"metadata": meta})

    def decode(self, data):
        params = {}
        for key, value in data.items():
            decoded = json.loads(base64.b64decode(value))
            params[key] = decoded
        return params

    def get(self):
        decoded = self.decode(get_secret_data(self.namespace, self.name))
        return decoded

    def wait(self):
        kube.wait_for_secret(self.namespace, self.name)


class BGPVPNSecret(JsonSecret):
    def __init__(self):
        super().__init__(
            namespace=settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
            name=settings.OSCTL_BGPVPN_NEIGHBOR_INFO_SECRET_NAME,
        )

    def get_peer_ips(self):
        data = self.get()
        peers = []
        for node_name, node_data in data.items():
            peer = node_data["bgp"]["source_ip"]
            peers.append(peer)
        return peers


class ProxySecret:
    """The secret supports next data format:
    data:
      HTTP_PROXY: {base64 encoded string}
      http_proxy: {base64 encoded string}
    """

    def __init__(self):
        self.namespace = settings.OSCTL_PROXY_SECRET_NAMESPACE
        self.name = settings.OSCTL_PROXY_DATA["secretName"]

    def decode(self, data):
        params = {}
        for key, value in data.items():
            decoded = base64.b64decode(value).decode()
            params[key] = decoded
        return params

    def wait(self):
        kube.wait_for_secret(self.namespace, self.name)

    def get_proxy_vars(self, no_proxy=None):
        data = self.decode(get_secret_data(self.namespace, self.name))
        proxy_vars = {}
        custom_vars = {}

        def _set_proxy_var(key, value):
            if key.lower() == "no_proxy" and no_proxy:
                value = ",".join(sorted(set(value.split(",")).union(no_proxy)))
            proxy_vars[key] = value
            # Different programs can parse upper or lower case
            # proxy variables.
            if key == key.lower():
                converted = key.upper()
            else:
                converted = key.lower()
            proxy_vars[converted] = value

        for key, value in data.items():
            if key in constants.PROXY_VARS_NAMES:
                _set_proxy_var(key, value)
            else:
                custom_vars[key.lower()] = value
        return proxy_vars, custom_vars
