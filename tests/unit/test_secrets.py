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
