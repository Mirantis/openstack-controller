import base64
import json
from unittest import mock

import pykube

from openstack_controller import secrets


def test_openstack_service_secret_name():
    secret = secrets.OpenStackServiceSecret("ns", "service")
    assert secret.secret_name == "generated-service-passwords"


@mock.patch("openstack_controller.secrets.generate_password")
def test_openstack_admin_secret_create_password(mock_password):
    password = "password"
    mock_password.return_value = password
    secret = secrets.OpenStackAdminSecret("ns")
    creds = secret.create()
    assert creds.database.username == "root"
    assert creds.database.password == password
    assert creds.identity.username == "admin"
    assert creds.identity.password == password
    assert creds.messaging.username == "rabbitmq"
    assert creds.messaging.password == password

    assert mock_password.call_count == 3


@mock.patch("openstack_controller.secrets.get_secret_data")
@mock.patch("openstack_controller.secrets.generate_password")
def test_keycloak_secret_serialization(mock_password, mock_data):
    passphrase = "passphrase"
    mock_password.return_value = passphrase

    secret_data = {
        "passphrase": base64.b64encode(json.dumps(passphrase).encode())
    }

    mock_data.side_effect = [pykube.exceptions.ObjectDoesNotExist, secret_data]

    secret = secrets.KeycloakSecret("ns")

    # NOTE(e0ne): ensure will create a secret if it's not found in K8S, so the
    # second call should just read the secret from the K8S.
    created = secret.ensure().passphrase
    from_secret = secret.ensure().passphrase

    assert created == passphrase
    assert created == from_secret


@mock.patch("openstack_controller.secrets.get_secret_data")
@mock.patch("openstack_controller.secrets.generate_password")
@mock.patch("openstack_controller.secrets.generate_name")
def test_galera_secret(mock_name, mock_password, mock_secret_data):
    creds_b64 = base64.b64encode(
        json.dumps({"username": "username", "password": "password"}).encode()
    )

    mock_name.return_value = "username"
    mock_password.return_value = "password"

    mock_secret_data.return_value = {
        "sst": creds_b64,
        "exporter": creds_b64,
        "audit": creds_b64,
    }
    galera_secret = secrets.GaleraSecret("ns")
    actual = galera_secret.get()

    system_creds = secrets.OSSytemCreds(
        username="username", password="password"
    )
    expected = secrets.GaleraCredentials(
        sst=system_creds,
        exporter=system_creds,
        audit=system_creds,
        backup=system_creds,
    )

    mock_name.assert_called_once_with(prefix="backup", length=8)
    mock_password.assert_called_once_with(length=32)
    mock_secret_data.assert_called_once_with("ns", galera_secret.secret_name)

    assert actual == expected
