from unittest import mock

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
