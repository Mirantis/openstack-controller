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
    } == await openstack_utils.get_keystone_admin_creds()


@pytest.mark.asyncio
async def test_get_keystone_admin_creds_timeout(
    kube_resource_list, asyncio_wait_for_timeout
):
    with pytest.raises(kopf.TemporaryError):
        await openstack_utils.get_keystone_admin_creds()


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
async def test_migrate_servers():
    conn_mock = mock.Mock(
        compute=mock.Mock(
            get_server=mock.Mock(
                return_value=mock.Mock(status="ACTIVE", hostname="buzz")
            )
        )
    )
    migrate_mock = mock.Mock(return_value=None)
    servers = ["a", "b", "c"]
    await openstack_utils.migrate_servers(
        openstack_connection=conn_mock,
        migrate_func=migrate_mock,
        servers=servers,
        migrating_off="bar",
    )
    migrate_mock.assert_has_calls([mock.call(s) for s in servers])
    conn_mock.compute.get_server.assert_has_calls(
        [mock.call(s) for s in servers]
    )


@pytest.mark.asyncio
async def test_migrate_servers_timeout(asyncio_wait_for_timeout):
    conn_mock = mock.Mock(
        compute=mock.Mock(
            get_server=mock.Mock(
                return_value=mock.Mock(status="MIGRATING", hostname="bar")
            )
        )
    )
    migrate_mock = mock.Mock(return_value=None)
    servers = ["a", "b", "c"]

    with pytest.raises(kopf.PermanentError):
        await openstack_utils.migrate_servers(
            openstack_connection=conn_mock,
            migrate_func=migrate_mock,
            servers=servers,
            migrating_off="bar",
        )
    migrate_mock.assert_has_calls([mock.call(s) for s in servers])
