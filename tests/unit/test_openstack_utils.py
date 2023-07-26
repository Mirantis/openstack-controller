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

import base64
from os import path
from unittest import mock
import copy
import openstack

from keystoneauth1 import exceptions as ksa_exceptions
import kopf
import pytest

from openstack_controller import openstack_utils
from openstack_controller import settings
from openstack_controller import kube


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


def _get_node(host="host1", role="compute"):
    node_obj = copy.deepcopy(NODE_OBJ)
    node_obj["metadata"]["name"] = host
    if role == "compute":
        node_obj["metadata"]["labels"] = {"openstack-compute-node": "enabled"}
    if role == "control":
        node_obj["metadata"]["labels"] = {"openstack-control-plane": "enabled"}
    return node_obj


@pytest.mark.asyncio
async def test_init_keystone_admin_creds_timeout(kube_resource_list):
    get_or_none_mock = mock.Mock()
    get_or_none_mock.return_value = None
    openstack_utils.ADMIN_CREDS = None

    kube_resource_list.return_value.get_or_none.return_value = None

    with pytest.raises(kopf.TemporaryError):
        openstack_utils.init_keystone_admin_creds()


@pytest.mark.asyncio
async def test_init_keystone_admin_creds_multiple_times(
    mocker, kube_resource_list
):
    file_exists_mock = mocker.patch.object(path, "exists")
    mocker.patch.object(
        settings, "OS_CLIENT_CONFIG_FILE", "/tmp/osctl-clouds.yaml"
    )
    file_exists_mock.side_effect = [False, True]
    kube_resource_list.return_value.get_or_none.return_value = mock.Mock(
        obj={
            "data": {
                "clouds.yaml": base64.b64encode("foo".encode("utf-8")),
            }
        }
    )
    openstack_utils.init_keystone_admin_creds()
    openstack_utils.init_keystone_admin_creds()
    kube_resource_list.assert_called_once()


@pytest.mark.asyncio
async def test_openstack_client_no_creds(mocker, openstack_connect):
    init_keystone_creds_mock = mocker.patch.object(
        openstack_utils, "init_keystone_admin_creds"
    )
    init_keystone_creds_mock.return_value = None

    openstack_utils.OpenStackClientManager()
    init_keystone_creds_mock.assert_called_once()


@mock.patch.object(openstack_utils, "OpenStackClientManager")
@pytest.mark.asyncio
async def test_notify_masakari_host_down(
    openstack_client_manager,
):
    node = kube.Node(mock.Mock, copy.deepcopy(_get_node()))
    await openstack_utils.notify_masakari_host_down(node)
    openstack_client_manager.return_value.instance_ha_create_notification.assert_called_once()


@mock.patch.object(openstack_utils, "OpenStackClientManager")
@pytest.mark.asyncio
async def test_notify_masakari_host_down_exception_unknown(
    openstack_client_manager,
):
    node = kube.Node(mock.Mock, copy.deepcopy(_get_node()))
    openstack_client_manager.side_effect = Exception("Boom")
    with pytest.raises(kopf.TemporaryError):
        await openstack_utils.notify_masakari_host_down(node)
    openstack_client_manager.return_value.instance_ha_create_notification.assert_not_called()


@mock.patch.object(openstack_utils, "OpenStackClientManager")
@pytest.mark.asyncio
async def test_notify_masakari_host_down_exception_no_masakari(
    openstack_client_manager,
):
    node = kube.Node(mock.Mock, copy.deepcopy(_get_node()))
    openstack_client_manager.side_effect = ksa_exceptions.EndpointNotFound(
        "Not found"
    )
    await openstack_utils.notify_masakari_host_down(node)
    openstack_client_manager.return_value.instance_ha_create_notification.assert_not_called()


@mock.patch.object(openstack_utils, "OpenStackClientManager")
@pytest.mark.asyncio
async def test_notify_masakari_host_down_host_not_in_segment_400(
    openstack_client_manager,
):
    node = kube.Node(mock.Mock, copy.deepcopy(_get_node()))
    openstack_client_manager.side_effect = openstack.exceptions.HttpException(
        f"Host with name {node.name} could not be found.", http_status=400
    )
    await openstack_utils.notify_masakari_host_down(node)
    openstack_client_manager.return_value.instance_ha_create_notification.assert_not_called()


@mock.patch.object(openstack_utils, "OpenStackClientManager")
@pytest.mark.asyncio
async def test_notify_masakari_host_down_host_not_in_segment_500(
    openstack_client_manager,
):
    node = kube.Node(mock.Mock, copy.deepcopy(_get_node()))
    openstack_client_manager.side_effect = openstack.exceptions.HttpException(
        f"Host with name {node.name} could not be found.", http_status=500
    )
    with pytest.raises(kopf.TemporaryError):
        await openstack_utils.notify_masakari_host_down(node)
    openstack_client_manager.return_value.instance_ha_create_notification.assert_not_called()


@mock.patch.object(openstack_utils, "OpenStackClientManager")
@pytest.mark.asyncio
async def test_notify_masakari_host_down_unknown(
    openstack_client_manager,
):
    node = kube.Node(mock.Mock, copy.deepcopy(_get_node()))
    openstack_client_manager.side_effect = Exception("Error")
    with pytest.raises(kopf.TemporaryError):
        await openstack_utils.notify_masakari_host_down(node)
    openstack_client_manager.return_value.instance_ha_create_notification.assert_not_called()
