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

from openstack_controller import kube
from openstack_controller import settings

settings.OSCTL_ENABLE_NODE_MAINTENANCE_REQUEST_PROCESSING = True

from openstack_controller.controllers import node_maintenance_request


# TODO(vdrok): Remove with switch to python3.8 as mock itself will be able
#              to handle async
class AsyncMock(mock.Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@pytest.fixture
def nova_registry_service(mocker):
    mock_service_class = mock.Mock()
    mocker.patch(
        "openstack_controller.controllers.node_maintenance_request.ORDERED_SERVICES",
        [("compute", mock_service_class)],
    )
    methods = [
        "prepare_node_after_reboot",
        "add_node_to_scheduling",
        "remove_node_from_scheduling",
        "prepare_for_node_reboot",
    ]
    for attr in methods:
        setattr(mock_service_class, attr, AsyncMock())
    yield mock_service_class
    mocker.stopall()


@pytest.mark.asyncio
async def test_maintenance_start(nova_registry_service):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = kube.NodeWorkloadLock(
        kube.api,
        {
            "metadata": {
                "name": "fake-nwl",
                "labels": {"openstack-compute-node": "enabled"},
            },
            "spec": {"nodeName": "fake-node", "controllerName": "openstack"},
            "status": {"state": "active"},
        },
    )

    values = []

    def set_state(value):
        values.append(value)

    nwl.set_state = set_state

    with mock.patch.object(kube, "find", return_value=nwl):
        await node_maintenance_request.node_maintenance_request_change_handler(
            nmr
        )

    assert values == ["prepare_inactive", "inactive"]


@pytest.mark.asyncio
async def test_maintenance_stop(nova_registry_service):
    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = kube.NodeWorkloadLock(
        kube.api,
        {
            "metadata": {
                "name": "fake-nwl",
                "labels": {"openstack-compute-node": "enabled"},
            },
            "spec": {"nodeName": "fake-node", "controllerName": "openstack"},
            "status": {"state": "inactive"},
        },
    )

    values = []

    def set_state(value):
        values.append(value)

    nwl.set_state = set_state

    with mock.patch.object(kube, "find", return_value=nwl):
        await node_maintenance_request.node_maintenance_request_delete_handler(
            nmr
        )

    assert values == ["prepare_active", "active"]


@pytest.mark.asyncio
async def test_maintenance_preparation_failure(nova_registry_service):
    nova_registry_service.prepare_node_after_reboot = AsyncMock(
        side_effect=kopf.PermanentError
    )

    nmr = {
        "metadata": {"name": "fake-nmr"},
        "spec": {"nodeName": "fake-node"},
    }
    nwl = kube.NodeWorkloadLock(
        kube.api,
        {
            "metadata": {
                "name": "fake-nwl",
                "labels": {"openstack-compute-node": "enabled"},
            },
            "spec": {"nodeName": "fake-node", "controllerName": "openstack"},
            "status": {"state": "active"},
        },
    )

    values = []

    def set_state(value):
        values.append(value)

    nwl.set_state = set_state

    with pytest.raises(kopf.PermanentError):
        with mock.patch.object(kube, "find", return_value=nwl):
            await node_maintenance_request.node_maintenance_request_change_handler(
                nmr
            )

    assert values == ["prepare_inactive", "failed"]
