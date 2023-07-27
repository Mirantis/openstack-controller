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

from unittest import mock
import copy
import openstack

from keystoneauth1 import exceptions as ksa_exceptions
import kopf
import pytest

from openstack_controller import openstack_utils
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
async def test_openstack_client_no_creds(mocker, openstack_connect):
    openstack_utils.OpenStackClientManager()


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
