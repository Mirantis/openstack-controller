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

from openstack_controller.controllers import node


# TODO(vdrok): Remove with switch to python3.8 as mock itself will be able
#              to handle async
class AsyncMock(mock.Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@pytest.fixture
def nova_registry_service(mocker):
    mock_service_class = mock.Mock()
    mocker.patch.dict(
        "openstack_controller.services.base.Service.registry",
        {"compute": mock_service_class},
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


@pytest.fixture
def get_node_if_annotation_still_present(mocker):
    mock_node = mocker.patch.object(
        node, "_get_node_if_annotation_still_present", return_value="node"
    )
    yield mock_node
    mocker.stopall()


@pytest.fixture
def patch_node_annotations(mocker):
    mock_node = mocker.patch.object(node, "_patch_node_annotations")
    yield mock_node
    mocker.stopall()


@pytest.mark.asyncio
async def test__run_methods_async(
    nova_registry_service,
    get_node_if_annotation_still_present,
    patch_node_annotations,
):
    await node.node_set_annotation_handler(
        {"name": "host1"},
        {},
        {"request.lcm.mirantis.com": "status"},
    )
    get_node_if_annotation_still_present.assert_has_calls(
        [
            mock.call({"name": "host1"}, "request.lcm.mirantis.com", "status"),
        ]
    )
    annotated_node = get_node_if_annotation_still_present.return_value
    patch_node_annotations.assert_has_calls(
        [
            mock.call(
                annotated_node,
                "workload.lcm.mirantis.com/openstack",
                "available",
            ),
        ]
    )


@pytest.mark.asyncio
async def test__run_methods_async_failure(
    nova_registry_service,
    get_node_if_annotation_still_present,
    patch_node_annotations,
):
    nova_registry_service.prepare_node_after_reboot = AsyncMock(
        side_effect=kopf.PermanentError
    )
    with pytest.raises(kopf.PermanentError):
        await node.node_set_annotation_handler(
            {"name": "host1"},
            {},
            {"request.lcm.mirantis.com": "status"},
        )
    get_node_if_annotation_still_present.assert_has_calls(
        [
            mock.call({"name": "host1"}, "request.lcm.mirantis.com", "status"),
        ]
    )
    annotated_node = get_node_if_annotation_still_present.return_value
    patch_node_annotations.assert_has_calls(
        [
            mock.call(
                annotated_node,
                [
                    "workload.lcm.mirantis.com/openstack_compute",
                    "workload.lcm.mirantis.com/openstack",
                ],
                "not_available",
            ),
        ]
    )
