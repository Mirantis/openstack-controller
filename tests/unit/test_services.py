#    Copyright 2020 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import asyncio
import copy
import logging
from unittest import mock

import kopf
import openstack
import pytest

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import secrets
from openstack_controller import services


# TODO(vdrok): Remove with switch to python3.8 as mock itself will be able
#              to handle async
class AsyncMock(mock.Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


class MockOsdpl:
    metadata = {"generation": 123}


NODE_OBJ = {
    "apiVersion": "v1",
    "kind": "Node",
    "metadata": {
        "name": "host1",
        "uid": "42",
        "labels": {
            "openstack-compute-node": "enabled",
        },
    },
}


@mock.patch.object(kube.OpenStackDeployment, "reload")
def test_get_osdpl(mock_reload, openstackdeployment, kubeapi, kube_resource):
    osdplstmock = mock.MagicMock()
    service = services.Nova(openstackdeployment, logging, osdplstmock)
    service._get_osdpl()
    mock_reload.assert_called_once()


@mock.patch("openstack_controller.secrets.generate_password")
@mock.patch.object(secrets, "get_secret_data")
def test_get_admin_creds(mock_data, mock_password, openstackdeployment):
    osdplstmock = mock.MagicMock()
    service = services.Nova(openstackdeployment, logging, osdplstmock)

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

    osdplstmock = mock.MagicMock()
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
    service = services.Keystone(openstackdeployment, logging, osdplstmock)
    identity_helmbundle = service.render()
    # check no modification in-place for openstackdeployment
    assert openstackdeployment_old == openstackdeployment
    assert identity_helmbundle["metadata"]["name"] == "openstack-identity"
    # check helmbundle has data from base.yaml
    assert (
        identity_helmbundle["spec"]["releases"][0]["values"]["pod"][
            "replicas"
        ]["api"]
        == 333
    )
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
    osdplstmock = mock.MagicMock()
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
    service = services.Nova(openstackdeployment, logging, osdplstmock)
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


# NOTE (e0ne): @mock.patch decorator doesn't work with coroutines


@pytest.mark.asyncio
async def test_service_apply(
    mocker, openstackdeployment, compute_helmbundle_all
):
    osdplstmock = mock.MagicMock()
    service = services.Nova(openstackdeployment, logging, osdplstmock)

    mock_render = mocker.patch.object(services.base.Service, "render")
    mock_render.return_value = compute_helmbundle_all

    mock_update_status = mocker.patch.object(services.Nova, "update_status")
    mock_ceph_secrets = mocker.patch.object(
        services.Nova, "ensure_ceph_secrets"
    )
    mock_info = mocker.patch.object(kopf, "info")
    mocker.patch("subprocess.check_call")

    helm_run_cmd = mocker.patch(
        "openstack_controller.helm.HelmManager.run_cmd",
        return_value=asyncio.Future(),
    )
    helm_run_cmd.return_value.set_result(["fake_stdout", "fake_stderr"])

    helm_list = mocker.patch(
        "openstack_controller.helm.HelmManager.list",
        return_value=asyncio.Future(),
    )
    helm_list.return_value.set_result([])
    mocker.patch.dict("os.environ", {"NODE_IP": "fake_ip"})

    await service.apply("test_event")

    mock_render.assert_called_once()
    mock_update_status.has_calls(
        [
            mock.call({"children": {service.resource_name: "Applying"}}),
            mock.call({"children": {service.resource_name: True}}),
        ]
    )
    mock_ceph_secrets.assert_called_once()
    mock_info.assert_called_once()
    helm_run_cmd.assert_called()


def test_default_service_account_list(openstackdeployment):
    osdplstmock = mock.MagicMock()
    service = services.Nova(openstackdeployment, logging, osdplstmock)
    accounts = [constants.OS_SERVICES_MAP[service.service], "test"]
    assert accounts == service.service_accounts


def test_heat_service_account_list(openstackdeployment):
    osdplstmock = mock.MagicMock()
    service = services.Heat(openstackdeployment, logging, osdplstmock)
    accounts = ["heat_trustee", "heat_stack_user", "heat", "test"]
    assert accounts == service.service_accounts


@pytest.fixture
def openstack_client(mocker):
    oc_client = mocker.patch(
        "openstack_controller.openstack_utils.OpenStackClientManager"
    )
    oc_client.return_value = mock.MagicMock()
    yield oc_client
    mocker.stopall()


@pytest.fixture
def node_maintenance_config(mocker):
    nmc = mocker.patch(
        "openstack_controller.maintenance.NodeMaintenanceConfig"
    )
    nmc.return_value = mock.MagicMock()
    yield nmc
    mocker.stopall()


@pytest.fixture
def find_nova_cell_setup_cron_job(mocker):
    mock_get_creds = mocker.patch(
        "openstack_controller.openstack_utils.find_nova_cell_setup_cron_job",
        AsyncMock(return_value={"metadata": {"name": "buzz"}}),
    )
    yield mock_get_creds
    mocker.stopall()


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot(
    mocker,
    openstack_client,
    kube_resource_list,
    find_nova_cell_setup_cron_job,
    kopf_adopt,
):
    mocker.patch("openstack_controller.kube.get_osdpl", mock.MagicMock())
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    kube_resource_list.return_value.get.return_value = mock.Mock(obj=None)
    compute_service = mock.Mock()
    compute_service.state = "up"
    openstack_client.return_value.compute_get_services.return_value = [
        compute_service
    ]
    with mock.patch.object(kube.Job, "create"):
        await services.Nova.prepare_node_after_reboot(node)


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_not_compute(
    get_keystone_admin_creds,
    openstack_client,
    kube_resource_list,
    find_nova_cell_setup_cron_job,
    kopf_adopt,
):
    node_obj = copy.deepcopy(NODE_OBJ)
    node_obj["metadata"]["labels"] = {}
    node = kube.Node(mock.Mock, node_obj)
    kube_resource_list.return_value.get.return_value = mock.Mock(obj=None)
    with mock.patch.object(kube.Job, "create"):
        await services.Nova.prepare_node_after_reboot(node)
        kube_resource_list.return_value.get.assert_not_called()


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_timeout(
    asyncio_wait_for_timeout,
    openstack_client,
):
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.prepare_node_after_reboot(node)


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_openstacksdk_exception(
    asyncio_wait_for_timeout, openstack_client
):

    openstack_client.side_effect = openstack.exceptions.SDKException("foo")
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.prepare_node_after_reboot(node)


@pytest.mark.asyncio
async def test_nova_add_node_to_scheduling(
    get_keystone_admin_creds, openstack_client
):
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    await services.Nova.add_node_to_scheduling(node)
    openstack_client.return_value.compute_get_services.assert_called_once_with(
        host="host1"
    )
    openstack_client.return_value.compute_ensure_service_enabled.assert_called_once()


@pytest.mark.asyncio
async def test_nova_add_node_to_scheduling_not_compute(openstack_client):
    node_obj = copy.deepcopy(NODE_OBJ)
    node_obj["metadata"]["labels"] = {}
    node = kube.Node(mock.Mock, node_obj)
    await services.Nova.add_node_to_scheduling(node)
    openstack_client.return_value.compute_get_services.assert_not_called()


@pytest.mark.asyncio
async def test_nova_add_node_to_scheduling_cannot_enable_service(
    openstack_client,
):
    openstack_client.side_effect = openstack.exceptions.SDKException("foo")
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.add_node_to_scheduling(node)


@pytest.mark.asyncio
async def test_nova_remove_node_from_scheduling(openstack_client):
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    await services.Nova.remove_node_from_scheduling(node)
    openstack_client.return_value.compute_get_services.assert_called_once()
    openstack_client.return_value.compute_ensure_service_disabled.assert_called_once()


@pytest.mark.asyncio
async def test_nova_remove_node_from_scheduling_not_compute(openstack_client):
    node_obj = copy.deepcopy(NODE_OBJ)
    node_obj["metadata"]["labels"] = {}
    node = kube.Node(mock.Mock, node_obj)
    await services.Nova.remove_node_from_scheduling(node)
    openstack_client.return_value.compute_get_services.assert_not_called()


@pytest.mark.asyncio
async def test_nova_remove_node_from_scheduling_cannot_disable_service(
    openstack_client,
):
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    openstack_client.return_value.compute_ensure_service_disabled.side_effect = openstack.exceptions.SDKException(
        "foo"
    )
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.remove_node_from_scheduling(node)


@pytest.mark.asyncio
async def test_nova_prepare_node_for_reboot(
    mocker, openstack_client, node_maintenance_config
):
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))

    with mock.patch.object(
        services.Nova, "_migrate_servers", AsyncMock()
    ) as mock_migrate:
        await services.Nova.prepare_node_for_reboot(node)
        mock_migrate.assert_called_once()


@pytest.mark.asyncio
async def test_nova_prepare_node_for_reboot_not_compute(
    openstack_client, node_maintenance_config
):
    node_obj = copy.deepcopy(NODE_OBJ)
    node_obj["metadata"]["labels"] = {}
    node = kube.Node(mock.Mock, node_obj)
    with mock.patch.object(
        services.Nova, "_migrate_servers", AsyncMock()
    ) as mock_migrate:
        await services.Nova.prepare_node_for_reboot(node)
        mock_migrate.assert_not_called()


@pytest.mark.asyncio
async def test_nova_prepare_node_for_reboot_sdk_exception(
    openstack_client, node_maintenance_config
):
    openstack_client.side_effect = openstack.exceptions.SDKException("foo")
    node = kube.Node(mock.Mock, copy.deepcopy(NODE_OBJ))
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.prepare_node_for_reboot(node)


@pytest.mark.asyncio
async def test_nova_migrate_servers_no_instances(
    openstack_client, node_maintenance_config
):
    openstack_client.compute_get_servers_valid_for_live_migration.return_value = (
        []
    )
    openstack_client.compute_get_all_servers.return_value = []

    node_maintenance_config.instance_migration_mode = "live"
    await services.Nova._migrate_servers(
        openstack_client, "host1", node_maintenance_config, 1
    )
    openstack_client.compute_get_all_servers.assert_called_once()
    openstack_client.compute_get_servers_valid_for_live_migration.assert_called_once()
    openstack_client.compute_get_servers_in_migrating_state.assert_not_called()


@pytest.mark.asyncio
async def test_nova_migrate_servers_skip(
    openstack_client, node_maintenance_config
):
    node_maintenance_config.instance_migration_mode = "skip"
    await services.Nova._migrate_servers(
        openstack_client, "host1", node_maintenance_config, 1
    )
    openstack_client.compute_get_all_servers.assert_not_called()
    openstack_client.compute_get_servers_valid_for_live_migration.assert_not_called()
    openstack_client.compute_get_servers_in_migrating_state.assert_not_called()


def _get_server_obj(obj=None):
    if obj is None:
        obj = {}
    srv = openstack.compute.v2.server.Server()
    for k, v in obj.items():
        setattr(srv, k, v)
    return srv


@pytest.mark.asyncio
async def test_nova_migrate_servers_manual_one_server(
    openstack_client, node_maintenance_config
):

    openstack_client.compute_get_servers_valid_for_live_migration.return_value = (
        []
    )
    openstack_client.compute_get_all_servers.return_value = [_get_server_obj()]

    node_maintenance_config.instance_migration_mode = "manual"
    with pytest.raises(kopf.TemporaryError):
        await services.Nova._migrate_servers(
            openstack_client, "host1", node_maintenance_config, 1
        )
    openstack_client.compute_get_all_servers.assert_called_once()
    openstack_client.compute_get_servers_valid_for_live_migration.assert_not_called()


@pytest.mark.asyncio
async def test_nova_migrate_servers_live_one_error_server(
    openstack_client, node_maintenance_config
):

    openstack_client.compute_get_servers_valid_for_live_migration.return_value = (
        []
    )
    srv = {"status": "ERROR"}
    openstack_client.compute_get_all_servers.return_value = [
        _get_server_obj(srv)
    ]

    node_maintenance_config.instance_migration_mode = "live"
    with pytest.raises(kopf.TemporaryError):
        await services.Nova._migrate_servers(
            openstack_client, "host1", node_maintenance_config, 1
        )
    openstack_client.compute_get_all_servers.assert_called_once()
    openstack_client.compute_get_servers_valid_for_live_migration.assert_called_once()


# vsaienko(TODO): add more tests covering logic in _do_servers_migration()
