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

import copy
import logging
from unittest import mock

import kopf
import openstack
import pykube
import pytest

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import openstack_utils
from openstack_controller import secrets
from openstack_controller import services


# TODO(vdrok): Remove with switch to python3.8 as mock itself will be able
#              to handle async
class AsyncMock(mock.Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


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


@pytest.fixture
def openstack_connect_with_compute_services(mocker):
    mock_connect = mocker.patch("openstack.connect")
    services_mock = mock.Mock(
        get=mock.Mock(
            return_value=mock.Mock(
                json=mock.Mock(
                    return_value={
                        "services": [
                            dict(
                                id=1,
                                binary="nova-compute",
                                host="host1",
                                status="enabled",
                                state="up",
                            )
                        ]
                    }
                ),
                status_code=200,
            )
        )
    )
    mock_connect.return_value = mock.Mock(compute=services_mock)
    yield mock_connect
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
    get_keystone_admin_creds,
    openstack_connect_with_compute_services,
    kube_resource_list,
    find_nova_cell_setup_cron_job,
    kopf_adopt,
):
    kube_resource_list.return_value.get.return_value = mock.Mock(obj=None)
    with mock.patch.object(kube.Job, "create"):
        await services.Nova.prepare_node_after_reboot(
            {"name": "host1", "uid": "42"}
        )


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_timeout(
    asyncio_wait_for_timeout,
    get_keystone_admin_creds,
    openstack_connect_with_compute_services,
):
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.prepare_node_after_reboot(
            {"name": "host3", "uid": "42"}
        )


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_openstacksdk_exception(
    asyncio_wait_for_timeout, get_keystone_admin_creds, openstack_connect
):
    services_mock = mock.Mock(
        services=mock.Mock(
            side_effect=openstack.exceptions.SDKException("foo")
        )
    )
    openstack_connect.return_value = mock.Mock(compute=services_mock)
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.prepare_node_after_reboot(
            {"name": "host3", "uid": "42"}
        )


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_osdpl_not_found(
    get_keystone_admin_creds,
    openstack_connect_with_compute_services,
    kube_resource_list,
    find_nova_cell_setup_cron_job,
    kopf_adopt,
):
    kube_resource_list.return_value.get.side_effect = Exception(
        "osdpl not found"
    )
    with mock.patch.object(kube.Job, "create"):
        with pytest.raises(kopf.PermanentError):
            await services.Nova.prepare_node_after_reboot(
                {"name": "host1", "uid": "42"}
            )


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_cannot_create_job(
    get_keystone_admin_creds,
    openstack_connect_with_compute_services,
    kube_resource_list,
    find_nova_cell_setup_cron_job,
    kopf_adopt,
):
    kube_resource_list.return_value.get.return_value = mock.Mock(obj=None)
    with mock.patch.object(kube.Job, "create") as mock_create_job:
        mock_create_job.side_effect = pykube.exceptions.HTTPError(
            message="foo", code=400
        )
        with pytest.raises(kopf.PermanentError):
            await services.Nova.prepare_node_after_reboot(
                {"name": "host1", "uid": "42"}
            )


@pytest.mark.asyncio
async def test_nova_prepare_node_after_reboot_job_already_exists(
    get_keystone_admin_creds,
    openstack_connect_with_compute_services,
    kube_resource_list,
    find_nova_cell_setup_cron_job,
    kopf_adopt,
):
    kube_resource_list.return_value.get.return_value = mock.Mock(obj=None)
    with mock.patch.object(kube, "Job") as mock_job:
        mock_job.return_value.create.side_effect = [
            pykube.exceptions.HTTPError(message="foo", code=409),
        ]
        with pytest.raises(kopf.TemporaryError):
            await services.Nova.prepare_node_after_reboot(
                {"name": "host1", "uid": "42"}
            )
        mock_job.return_value.delete.assert_called_once_with()


@pytest.mark.asyncio
async def test_nova_add_node_to_scheduling(
    get_keystone_admin_creds, openstack_connect_with_compute_services
):
    await services.Nova.add_node_to_scheduling({"name": "host1", "uid": "42"})
    os_connection = openstack_connect_with_compute_services.return_value
    os_connection.compute.enable_service.assert_called_once_with(
        1, "host1", "nova-compute"
    )


@pytest.mark.asyncio
async def test_nova_add_node_to_scheduling_timeout_enabling_service(
    get_keystone_admin_creds,
    openstack_connect_with_compute_services,
    asyncio_wait_for_timeout,
):
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.add_node_to_scheduling(
            {"name": "host1", "uid": "42"}
        )


@pytest.mark.asyncio
async def test_nova_add_node_to_scheduling_cannot_enable_service(
    get_keystone_admin_creds, openstack_connect_with_compute_services
):
    os_connection = openstack_connect_with_compute_services.return_value
    os_connection.compute.enable_service = mock.Mock(
        side_effect=openstack.exceptions.SDKException("foo")
    )
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.add_node_to_scheduling(
            {"name": "host1", "uid": "42"}
        )


@pytest.mark.asyncio
async def test_nova_remove_node_from_scheduling(
    get_keystone_admin_creds, openstack_connect
):
    services_mock = mock.Mock(
        get=mock.Mock(
            return_value=mock.Mock(
                json=mock.Mock(
                    side_effect=[
                        {
                            "services": [
                                dict(id=1, state="up", status="enabled")
                            ]
                        },
                        {
                            "services": [
                                dict(id=1, state="up", status="disabled")
                            ]
                        },
                    ]
                ),
                status_code=200,
            )
        )
    )
    openstack_connect.return_value = mock.Mock(compute=services_mock)
    await services.Nova.remove_node_from_scheduling(
        {"name": "host1", "uid": "42"}
    )
    services_mock.disable_service.assert_called_once_with(
        1, "host1", "nova-compute"
    )


@pytest.mark.asyncio
async def test_nova_remove_node_from_scheduling_service_down(
    get_keystone_admin_creds, openstack_connect
):
    services_mock = mock.Mock(
        get=mock.Mock(
            return_value=mock.Mock(
                json=mock.Mock(
                    return_value={
                        "services": [
                            dict(id=1, state="down", status="enabled")
                        ]
                    }
                ),
                status_code=200,
            )
        )
    )
    openstack_connect.return_value = mock.Mock(compute=services_mock)
    await services.Nova.remove_node_from_scheduling(
        {"name": "host1", "uid": "42"}
    )
    services_mock.disable_service.assert_not_called()


@pytest.mark.asyncio
async def test_nova_remove_node_from_scheduling_timeout(
    get_keystone_admin_creds,
    openstack_connect_with_compute_services,
    asyncio_wait_for_timeout,
):
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.remove_node_from_scheduling(
            {"name": "host1", "uid": "42"}
        )
    os_connection = openstack_connect_with_compute_services.return_value
    os_connection.compute.disable_service.assert_called_once_with(
        1, "host1", "nova-compute"
    )


@pytest.mark.asyncio
async def test_nova_remove_node_from_scheduling_cannot_disable_service(
    get_keystone_admin_creds, openstack_connect_with_compute_services
):
    os_connection = openstack_connect_with_compute_services.return_value
    os_connection.compute.disable_service = mock.Mock(
        side_effect=openstack.exceptions.SDKException("foo")
    )
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.remove_node_from_scheduling(
            {"name": "host1", "uid": "42"}
        )


@pytest.mark.asyncio
async def test_nova_prepare_for_node_reboot(
    get_keystone_admin_creds, openstack_connect_with_compute_services
):
    with mock.patch.object(
        openstack_utils, "migrate_servers", AsyncMock()
    ) as mock_migrate:
        os_connection = openstack_connect_with_compute_services.return_value
        os_connection.compute.servers = mock.Mock(return_value=["a", "b", "c"])
        await services.Nova.prepare_for_node_reboot({"name": "host1"})
        mock_migrate.assert_called_once_with(
            openstack_connection=os_connection,
            migrate_func=os_connection.compute.live_migrate_server,
            servers=["a", "b", "c"],
            migrating_off="host1",
            concurrency=5,
        )


@pytest.mark.asyncio
async def test_nova_prepare_for_node_reboot_evacuate_disabled_by_default(
    get_keystone_admin_creds, openstack_connect
):
    compute_mock = mock.Mock(
        get=mock.Mock(
            return_value=mock.Mock(
                json=mock.Mock(
                    return_value={
                        "services": [
                            dict(id=1, state="down", status="enabled")
                        ]
                    }
                ),
                status_code=200,
            )
        ),
        servers=mock.Mock(return_value=["a", "b", "c"]),
    )
    openstack_connect.return_value = mock.Mock(compute=compute_mock)
    with mock.patch.object(
        openstack_utils, "migrate_servers", AsyncMock()
    ) as mock_migrate:
        with pytest.raises(kopf.PermanentError):
            await services.Nova.prepare_for_node_reboot({"name": "host1"})
        mock_migrate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override_setting",
    [{"name": "OSCTL_ALLOW_EVACUATION", "value": True}],
    indirect=["override_setting"],
)
async def test_nova_prepare_for_node_reboot_evacuate(
    override_setting, get_keystone_admin_creds, openstack_connect
):
    compute_mock = mock.Mock(
        get=mock.Mock(
            return_value=mock.Mock(
                json=mock.Mock(
                    return_value={
                        "services": [
                            dict(id=1, state="down", status="enabled")
                        ]
                    }
                ),
                status_code=200,
            )
        ),
        servers=mock.Mock(return_value=["a", "b", "c"]),
    )
    openstack_connect.return_value = mock.Mock(compute=compute_mock)
    with mock.patch.object(
        openstack_utils, "migrate_servers", AsyncMock()
    ) as mock_migrate:
        await services.Nova.prepare_for_node_reboot({"name": "host1"})
        mock_migrate.assert_called_once_with(
            openstack_connection=openstack_connect.return_value,
            migrate_func=compute_mock.evacuate_server,
            servers=["a", "b", "c"],
            migrating_off="host1",
            concurrency=5,
        )


@pytest.mark.asyncio
async def test_nova_prepare_for_node_reboot_sdk_exception(
    get_keystone_admin_creds, openstack_connect
):
    compute_mock = mock.Mock(
        get=mock.Mock(side_effect=openstack.exceptions.SDKException("foo"))
    )
    openstack_connect.return_value = mock.Mock(compute=compute_mock)
    with pytest.raises(kopf.TemporaryError):
        await services.Nova.prepare_for_node_reboot(
            {"name": "host1", "uid": "42"}
        )
