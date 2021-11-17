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

import kopf
import pytest

from openstack_controller.controllers import (
    maintenance as maintenance_controller,
)
from openstack_controller import maintenance
from openstack_controller import kube


# TODO(vdrok): Remove with switch to python3.8 as mock itself will be able
#              to handle async
class AsyncMock(mock.Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@pytest.fixture
def nova_registry_service(mocker):
    mock_service_class = mock.Mock()
    mock_service_class.return_value = mock.AsyncMock()
    mocker.patch(
        "openstack_controller.controllers.maintenance.ORDERED_SERVICES",
        [("compute", mock_service_class)],
    )
    methods = [
        "process_nmr",
        "delete_nmr",
        "prepare_node_after_reboot",
        "add_node_to_scheduling",
        "remove_node_from_scheduling",
        "prepare_node_for_reboot",
    ]
    for attr in methods:
        setattr(mock_service_class.return_value, attr, AsyncMock())
    yield mock_service_class
    mocker.stopall()


@pytest.fixture
def osdpl(mocker):
    osdpl = mocker.patch("openstack_controller.kube.get_osdpl")
    osdpl.return_value = mock.AsyncMock()
    yield osdpl
    mocker.stopall()


@pytest.fixture
def node(mocker):
    node = mocker.patch("openstack_controller.kube.Node")
    node.return_value = mock.AsyncMock()
    node.return_value.name = "fake-node"
    yield node
    mocker.stopall()


@pytest.mark.asyncio
async def test_nmr_change_not_required_for_node(
    mocker, nova_registry_service, node
):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = mock.Mock()
    nwl.required_for_node.return_value = False
    mocker.patch.object(
        maintenance.NodeWorkloadLock, "get_resource", return_value=nwl
    )

    node.return_value.ready = True
    mocker.patch.object(kube, "find", side_effect=(node,))
    await maintenance_controller.node_maintenance_request_change_handler(
        nmr, diff=()
    )
    nwl.required_for_node.assert_called_once()
    nwl.present.assert_not_called()
    nwl.is_maintenance.assert_not_called()
    nwl.is_active.assert_not_called()
    nwl.set_state_inactive.assert_not_called()


@pytest.mark.asyncio
async def test_nmr_change_required_for_node_not_maintenance_0_active_lock(
    mocker, nova_registry_service, osdpl, node
):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = mock.Mock()
    nwl.required_for_node.return_value = True
    nwl.is_maintenance.return_value = False
    nwl.maintenance_locks.return_value = []

    osdpl.exists.return_value = True

    mocker.patch.object(
        maintenance.NodeWorkloadLock, "get_resource", return_value=nwl
    )

    node.return_value.ready = True
    mocker.patch.object(kube, "find", side_effect=(node,))
    await maintenance_controller.node_maintenance_request_change_handler(
        nmr, diff=()
    )
    nwl.required_for_node.assert_called_once()
    nwl.present.assert_called_once()
    nwl.is_maintenance.assert_called_once()
    nwl.is_active.assert_called_once()
    nwl.set_state_inactive.assert_called_once()


@pytest.mark.asyncio
async def test_nmr_change_required_for_node_not_maintenance_1_active_lock(
    mocker, nova_registry_service, osdpl, node
):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = mock.Mock()
    nwl.required_for_node.return_value = True
    nwl.is_maintenance.return_value = False
    nwl.maintenance_locks.return_value = [1]

    osdpl.exists.return_value = True

    mocker.patch.object(
        maintenance.NodeWorkloadLock, "get_resource", return_value=nwl
    )

    node.return_value.ready = True
    mocker.patch.object(kube, "find", side_effect=(node,))
    with pytest.raises(kopf.TemporaryError):
        await maintenance_controller.node_maintenance_request_change_handler(
            nmr, diff=()
        )
    nwl.required_for_node.assert_called_once()
    nwl.present.assert_called_once()
    nwl.is_maintenance.assert_called_once()
    nwl.is_active.assert_not_called()
    nwl.set_state_inactive.assert_not_called()


@pytest.mark.asyncio
async def test_nmr_change_required_for_node_maintenance_1_active_lock(
    mocker, nova_registry_service, osdpl, node
):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = mock.Mock()
    nwl.required_for_node.return_value = True
    nwl.is_maintenance.return_value = True
    nwl.maintenance_locks.return_value = [1]

    osdpl.exists.return_value = True

    mocker.patch.object(
        maintenance.NodeWorkloadLock, "get_resource", return_value=nwl
    )

    node.return_value.ready = True
    mocker.patch.object(kube, "find", side_effect=(node,))
    await maintenance_controller.node_maintenance_request_change_handler(
        nmr, diff=()
    )
    nova_registry_service.return_value.process_nmr.assert_called_once()
    nwl.required_for_node.assert_called_once()
    nwl.present.assert_called_once()
    nwl.is_maintenance.assert_called_once()
    nwl.is_active.assert_called_once()
    nwl.set_state_inactive.assert_called_once()


@pytest.mark.asyncio
async def test_nmr_delete_stop_not_required_for_node(
    mocker, nova_registry_service, osdpl, node
):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = mock.Mock()
    nwl.required_for_node.return_value = False
    mocker.patch.object(
        maintenance.NodeWorkloadLock, "get_resource", return_value=nwl
    )

    node.return_value.ready = True
    osdpl.exists.return_value = True

    mocker.patch.object(kube, "find", side_effect=(node,))
    await maintenance_controller.node_maintenance_request_delete_handler(nmr)
    nwl.required_for_node.assert_called_once()
    nwl.absent.assert_called_once()
    nwl.is_maintenance.assert_not_called()
    nwl.set_inner_state_inactive.assert_not_called()
    nwl.set_state_active.assert_not_called()


@pytest.mark.asyncio
async def test_nmr_delete_nwl_not_in_maintenance(
    mocker, nova_registry_service, osdpl, node
):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = mock.Mock()
    nwl.required_for_node.return_value = True
    nwl.is_maintenance.return_value = False
    mocker.patch.object(
        maintenance.NodeWorkloadLock, "get_resource", return_value=nwl
    )

    osdpl.exists.return_value = True
    node.return_value.ready = True

    mocker.patch.object(kube, "find", side_effect=(node,))
    await maintenance_controller.node_maintenance_request_delete_handler(nmr)
    nwl.required_for_node.assert_called_once()
    nwl.absent.assert_not_called()
    nwl.is_maintenance.assert_called()
    nwl.set_inner_state_inactive.assert_called_once()
    nwl.set_state_active.assert_called_once()


@pytest.mark.asyncio
async def test_nmr_delete_nwl_in_maintenance(
    mocker, nova_registry_service, osdpl, node
):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = mock.Mock()
    nwl.required_for_node.return_value = True
    nwl.is_maintenance.return_value = True
    mocker.patch.object(
        maintenance.NodeWorkloadLock, "get_resource", return_value=nwl
    )

    node.return_value.ready = True

    osdpl.exists.return_value = True
    nova_registry_service.return_value.maintenance_api.return_value = True
    mocker.patch.object(kube, "find", side_effect=(node,))
    await maintenance_controller.node_maintenance_request_delete_handler(nmr)
    nwl.required_for_node.assert_called_once()
    nova_registry_service.return_value.delete_nmr.assert_called_once()
    nwl.absent.assert_not_called()
    nwl.is_maintenance.assert_called()
    nwl.set_inner_state_inactive.assert_called_once()
    nwl.set_state_active.assert_called_once()
