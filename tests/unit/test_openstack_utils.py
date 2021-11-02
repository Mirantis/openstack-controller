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
from unittest import mock

import kopf
import pytest

from openstack_controller import openstack_utils


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


@pytest.mark.asyncio
async def test_get_keystone_admin_creds(kube_resource_list):
    kube_resource_list.return_value.get_or_none.return_value = mock.Mock(
        obj={
            "data": {
                "OS_FF": base64.b64encode("foo".encode("utf-8")),
                "BAR": base64.b64encode("bar".encode("utf-8")),
            }
        }
    )
    assert {
        "ff": "foo",
        "bar": "bar",
    } == openstack_utils.get_keystone_admin_creds()


@pytest.mark.asyncio
async def test_get_keystone_admin_creds_timeout(kube_resource_list):
    get_or_none_mock = mock.Mock()
    get_or_none_mock.return_value = None
    openstack_utils.ADMIN_CREDS = None

    kube_resource_list.return_value.get_or_none.return_value = None

    with pytest.raises(kopf.TemporaryError):
        openstack_utils.get_keystone_admin_creds()


@pytest.mark.asyncio
async def test_get_keystone_admin_creds_multiple_times(kube_resource_list):
    kube_resource_list.return_value.get_or_none.return_value = mock.Mock(
        obj={
            "data": {
                "OS_FF": base64.b64encode("foo".encode("utf-8")),
                "BAR": base64.b64encode("bar".encode("utf-8")),
            }
        }
    )
    openstack_utils.get_keystone_admin_creds()
    openstack_utils.get_keystone_admin_creds()
    kube_resource_list.assert_called_once()


@pytest.mark.asyncio
async def test_find_nova_cell_setup_cron_job(kube_resource_list):
    kube_resource_list.return_value.get_or_none.return_value = mock.Mock(
        obj={
            "metadata": {"annotations": ["foo"]},
            "spec": {
                "jobTemplate": {
                    "spec": {"template": {"spec": {}}},
                    "metadata": {"labels": ["buzz"]},
                }
            },
        }
    )
    res = await openstack_utils.find_nova_cell_setup_cron_job(node_uid="bar")
    assert {
        "metadata": {
            "name": "nova-cell-setup-online-bar",
            "namespace": "openstack",
            "annotations": ["foo"],
            "labels": ["buzz"],
        },
        "spec": {
            "backoffLimit": 10,
            "ttlSecondsAfterFinished": 60,
            "template": {"spec": {"restartPolicy": "OnFailure"}},
        },
    } == res


@pytest.mark.asyncio
async def test_find_nova_cell_setup_cron_job_timeout(
    kube_resource_list, asyncio_wait_for_timeout
):
    with pytest.raises(kopf.TemporaryError):
        await openstack_utils.find_nova_cell_setup_cron_job(node_uid="ff")


@pytest.mark.asyncio
async def test_openstack_client_no_creds(mocker, openstack_connect):
    get_keystone_creds_mock = mocker.patch.object(
        openstack_utils, "get_keystone_admin_creds"
    )
    get_keystone_creds_mock.return_value = {"ff": "foo", "bar": "bar"}

    openstack_utils.OpenStackClientManager()
    get_keystone_creds_mock.assert_called_once()
    openstack_connect.assert_called_once_with(ff="foo", bar="bar")


@pytest.mark.asyncio
async def test_openstack_client_creds(mocker, openstack_connect):
    get_keystone_creds_mock = mocker.patch.object(
        openstack_utils, "get_keystone_admin_creds"
    )
    creds = {"ff": "foo", "bar": "bar"}
    openstack_utils.OpenStackClientManager(creds)
    get_keystone_creds_mock.assert_not_called()
    openstack_connect.assert_called_once_with(**creds)
