from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import (
    serialization as crypto_serialization,
)
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import (
    default_backend as crypto_default_backend,
)
import datetime
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


def _generate_ssh_key(bits=2048) -> secrets.SshKey:
    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
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
    return secrets.SshKey(
        public=public_key.decode(), private=private_key.decode()
    )


def get_or_create_ssh_credentials(
    service: str, namespace: str,
) -> secrets.SshKey:
    secret_name = f"generated-{service}-ssh-creds"
    try:
        ssh_creds = secrets.get_ssh_secret(secret_name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        ssh_creds = _generate_ssh_key()
        secrets.save_ssh_secret(secret_name, namespace, ssh_creds)

    return ssh_creds


def get_or_create_galera_credentials(
    namespace: str,
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
            database={}, messaging={}, notifications={}, memcached=""
        )
        srv = OS_SERVICES_MAP.get(service)
        if srv:
            for service_type in ["database", "messaging", "notifications"]:
                getattr(os_creds, service_type)[
                    "user"
                ] = _generate_credentials(srv)
            os_creds.memcached = secrets.generate_password(length=16)
        elif service == "powerdns":
            os_creds.database["user"] = _generate_credentials(service)
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
    return admin_creds


def get_admin_credentials(namespace: str) -> secrets.OpenStackAdminCredentials:
    return secrets.get_os_admin_secret(ADMIN_SECRET_NAME, namespace)


def get_or_create_admin_credentials(
    namespace,
) -> secrets.OpenStackAdminCredentials:
    try:
        return get_admin_credentials(namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        return create_admin_credentials(namespace)


def get_or_create_certs(name, namespace) -> secrets.SingedCertificate:
    try:
        return secrets.SingedCertificate(
            **secrets.get_secret_data(namespace, name)
        )
    except pykube.exceptions.ObjectDoesNotExist:
        return generate_ca_cert(name, namespace)


def generate_ca_cert(name: str, namespace: str) -> secrets.SingedCertificate:
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=crypto_default_backend()
    )
    builder = x509.CertificateBuilder()

    issuer = x509.Name(
        [
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(x509.oid.NameOID.STATE_OR_PROVINCE_NAME, "CA"),
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
    client_cert = certificate.public_bytes(crypto_serialization.Encoding.PEM)
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
    signed_cert = secrets.SingedCertificate(**data)
    secrets.save_cert_secret(name, namespace, signed_cert)

    return signed_cert
