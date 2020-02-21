import copy
import logging
from unittest import mock

import kopf
import pytest

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import secrets
from openstack_controller import services


class MockOsdpl:
    metadata = {"generation": 123}


@mock.patch.object(kube.OpenStackDeployment, "reload")
def test_get_osdpl(mock_reload, openstackdeployment, kubeapi):
    service = services.Nova(openstackdeployment, logging)
    service._get_osdpl()
    mock_reload.assert_called_once()


@mock.patch("openstack_controller.secrets.generate_password")
@mock.patch.object(secrets, "get_secret_data")
def test_get_admin_creds(mock_data, mock_password, openstackdeployment):
    service = services.Nova(openstackdeployment, logging)

    mock_password.return_value = "password"
    mock_data.return_value = {
        "database": "eyJ1c2VybmFtZSI6ICJyb290IiwgInBhc3N3b3JkIjogInBhc3N3b3JkIn0=",
        "identity": "eyJ1c2VybmFtZSI6ICJhZG1pbiIsICJwYXNzd29yZCI6ICJwYXNzd29yZCJ9",
        "messaging": "eyJ1c2VybmFtZSI6ICJyYWJiaXRtcSIsICJwYXNzd29yZCI6ICJwYXNzd29yZCJ9",
    }

    expected_secret = secrets.OpenStackAdminSecret("namespace")
    expected_creds = expected_secret.create()

    admin_creeds = service._get_admin_creds()
    assert expected_creds.database.username == admin_creeds.database.username
    assert expected_creds.database.password == admin_creeds.database.password
    assert expected_creds.identity.username == admin_creeds.identity.username
    assert expected_creds.identity.password == admin_creeds.identity.password
    assert expected_creds.messaging.username == admin_creeds.messaging.username
    assert expected_creds.messaging.password == admin_creeds.messaging.password


@mock.patch.object(services.Keystone, "template_args")
@mock.patch.object(services.base.Service, "_get_osdpl")
def test_service_keystone_render(
    mock_osdpl, mock_template_args, openstackdeployment, kubeapi
):

    creds = secrets.OSSytemCreds("test", "test")
    admin_creds = secrets.OpenStackAdminCredentials(creds, creds, creds)
    creds_dict = {"user": creds, "admin": creds}
    credentials = secrets.OpenStackCredentials(
        database=creds_dict,
        messaging=creds_dict,
        notifications=creds_dict,
        memcached="secret",
    )
    service_creds = [secrets.OSServiceCreds("test", "test", "test")]

    mock_osdpl.return_value = MockOsdpl()
    mock_template_args.return_value = {
        "credentials": credentials,
        "admin_creds": admin_creds,
        "service_creds": service_creds,
    }
    openstackdeployment["spec"]["common"]["openstack"] = {
        "values": {"pod": {"replicas": {"api": 333}}}
    }
    openstackdeployment_old = copy.deepcopy(openstackdeployment)
    service = services.Keystone(openstackdeployment, logging)
    identity_helmbundle = service.render()
    # check no modification in-place for openstackdeployment
    assert (
        openstackdeployment["spec"]["common"]["openstack"]["values"]["pod"][
            "replicas"
        ]["api"]
        == 333
    )
    assert openstackdeployment_old == openstackdeployment
    assert identity_helmbundle["metadata"]["name"] == "openstack-identity"
    # check helmbundle has data from base.yaml
    assert identity_helmbundle["spec"]["releases"][0]["values"]["images"][
        "tags"
    ]


@mock.patch.object(services.base.OpenStackServiceWithCeph, "ceph_config")
@mock.patch.object(secrets.SSHSecret, "ensure")
@mock.patch.object(services.base.Service, "template_args")
@mock.patch.object(services.base.Service, "_get_osdpl")
def test_service_nova_with_ceph_render(
    mock_osdpl,
    mock_template_args,
    mock_ssh,
    mock_ceph_template_args,
    openstackdeployment,
    kubeapi,
):
    creds = secrets.OSSytemCreds("test", "test")
    admin_creds = secrets.OpenStackAdminCredentials(creds, creds, creds)
    creds_dict = {"user": creds, "admin": creds}
    credentials = secrets.OpenStackCredentials(
        database=creds_dict,
        messaging=creds_dict,
        notifications=creds_dict,
        memcached="secret",
    )
    service_creds = [secrets.OSServiceCreds("test", "test", "test")]

    mock_ssh.return_value = secrets.SshKey("public", "private")
    mock_osdpl.return_value = MockOsdpl()
    mock_template_args.return_value = {
        "credentials": credentials,
        "admin_creds": admin_creds,
        "service_creds": service_creds,
    }

    mock_ceph_template_args.return_value = {
        "ceph": {
            "nova": {
                "username": "nova",
                "keyring": "key",
                "secrets": [],
                "pools": {},
            }
        }
    }

    openstackdeployment_old = copy.deepcopy(openstackdeployment)
    service = services.Nova(openstackdeployment, logging)
    compute_helmbundle = service.render()
    # check no modification in-place for openstackdeployment
    assert openstackdeployment_old == openstackdeployment
    assert compute_helmbundle["metadata"]["name"] == "openstack-compute"
    # check helmbundle has data from base.yaml
    assert compute_helmbundle["spec"]["releases"][0]["values"]["images"][
        "tags"
    ]

    mock_ssh.assert_called_once()
    mock_ceph_template_args.assert_called_once()


# NOTE (e0ne): @mock.path decorator doesn't work with coroutines


@pytest.mark.asyncio
async def test_service_apply(mocker, openstackdeployment, compute_helmbundle):
    service = services.Nova(openstackdeployment, logging)

    mock_render = mocker.patch.object(services.base.Service, "render")
    mock_render.return_value = compute_helmbundle

    mock_update_status = mocker.patch.object(services.Nova, "update_status")
    mocck_ceeph_secrets = mocker.patch.object(
        services.Nova, "ensure_ceph_secrets"
    )
    mock_adopt = mocker.patch.object(kopf, "adopt")
    mock_resource = mocker.patch.object(kube, "resource")
    mock_info = mocker.patch.object(kopf, "info")

    await service.apply("test_event")

    mock_render.assert_called_once()
    mock_update_status.assert_called_once_with(
        {"children": {service.resource_name: "Unknown"}}
    )
    mocck_ceeph_secrets.assert_called_once()
    mock_adopt.assert_called_once_with(compute_helmbundle, service.osdpl.obj)
    mock_resource.assert_called_with(compute_helmbundle)
    assert mock_resource.call_count == 2
    mock_info.assert_called_once()


def test_default_service_account_list(openstackdeployment):
    service = services.Nova(openstackdeployment, logging)
    accounts = [constants.OS_SERVICES_MAP[service.service], "test"]
    assert accounts == service.service_accounts


def test_heat_service_account_list(openstackdeployment):
    service = services.Heat(openstackdeployment, logging)
    accounts = ["heat_trustee", "heat_stack_user", "heat", "test"]
    assert accounts == service.service_accounts
