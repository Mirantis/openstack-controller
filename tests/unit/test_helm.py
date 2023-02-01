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
import json

import pytest

from openstack_controller import helm
from openstack_controller import exception


def get_helm_release(name):
    return {
        "name": name,
    }


@pytest.fixture
def single_helm_release():
    return bytes(json.dumps([get_helm_release("test-release")]), "utf-8")


@pytest.fixture
def release_values():
    return bytes(json.dumps({"opt": "value"}), "utf-8")


@pytest.fixture
def subprocess_shell(mocker):
    mock_get_creds = mocker.patch(
        "asyncio.create_subprocess_shell",
        mock.AsyncMock(),
    )
    yield mock_get_creds
    mocker.stopall()


@pytest.fixture
def kube_wait_for_deleted(mocker):
    mock_get_obj = mocker.patch(
        "openstack_controller.kube.wait_for_deleted",
        mock.AsyncMock(),
    )
    yield mock_get_obj
    mocker.stopall()


@pytest.fixture
def kube_get_object_by_kind(mocker):
    mock_get_obj = mocker.patch(
        "openstack_controller.kube.get_object_by_kind",
        mock.AsyncMock(),
    )
    yield mock_get_obj
    mocker.stopall()


@pytest.fixture
def kube_find(mocker):
    mock_get_obj = mocker.patch(
        "openstack_controller.kube.find",
        mock.Mock(),
    )
    yield mock_get_obj
    mocker.stopall()


@pytest.mark.asyncio
async def test_exists(subprocess_shell, single_helm_release):
    hc = helm.HelmManager()
    subprocess_shell.return_value.communicate.return_value = (
        single_helm_release,
        b"",
    )
    subprocess_shell.return_value.returncode = 0
    expected_cmd = [
        "helm3",
        "list",
        "--namespace",
        "openstack",
        "-o",
        "json",
        "custom",
        "arg",
    ]

    assert await hc.exist("test-release", args=["custom", "arg"])
    subprocess_shell.assert_called_once_with(
        " ".join(expected_cmd),
        env=mock.ANY,
        stdin=mock.ANY,
        stdout=mock.ANY,
        stderr=mock.ANY,
    )


@pytest.mark.asyncio
async def test_exists_not_exist(subprocess_shell, single_helm_release):
    hc = helm.HelmManager()
    subprocess_shell.return_value.communicate.return_value = (
        single_helm_release,
        b"",
    )
    subprocess_shell.return_value.returncode = 0
    assert (
        await hc.exist("test-release-not-exist", args=["custom", "arg"])
        == None
    )


@pytest.mark.asyncio
async def test_list(subprocess_shell, single_helm_release):
    hc = helm.HelmManager()
    subprocess_shell.return_value.communicate.return_value = (
        single_helm_release,
        b"",
    )
    subprocess_shell.return_value.returncode = 0
    expected_cmd = [
        "helm3",
        "list",
        "--namespace",
        "openstack",
        "-o",
        "json",
        "custom",
        "arg",
    ]

    res = await hc.list(args=["custom", "arg"])
    assert json.loads(single_helm_release) == res
    subprocess_shell.assert_called_once_with(
        " ".join(expected_cmd),
        env=mock.ANY,
        stdin=mock.ANY,
        stdout=mock.ANY,
        stderr=mock.ANY,
    )


@pytest.mark.asyncio
async def test_get_release_values(subprocess_shell, release_values):
    hc = helm.HelmManager()
    subprocess_shell.return_value.communicate.return_value = (
        release_values,
        b"",
    )
    subprocess_shell.return_value.returncode = 0
    expected_cmd = [
        "helm3",
        "get",
        "values",
        "--namespace",
        "openstack",
        "test-release",
        "-o",
        "json",
        "custom",
        "arg",
    ]

    res = await hc.get_release_values("test-release", args=["custom", "arg"])
    assert json.loads(release_values) == res
    subprocess_shell.assert_called_once_with(
        " ".join(expected_cmd),
        env=mock.ANY,
        stdin=mock.ANY,
        stdout=mock.ANY,
        stderr=mock.ANY,
    )


@pytest.mark.asyncio
async def test_install_remove_immutable_1_item(
    subprocess_shell,
    kube_get_object_by_kind,
    kube_find,
    kube_wait_for_deleted,
    helm_error_1_item,
):
    hc = helm.HelmManager()
    subprocess_shell.return_value.returncode = 1
    subprocess_shell.return_value.communicate.return_value = (
        b"",
        helm_error_1_item,
    )
    kube_find.return_value = mock.AsyncMock()
    kube_get_object_by_kind.return_value = mock.AsyncMock()

    with pytest.raises(exception.HelmImmutableFieldChange):
        await hc.run_cmd("helm upgrade --install test-release")
    kube_find.assert_called_with(
        mock.ANY, "cinder-create-internal-tenant", "openstack", silent=True
    )
    kube_get_object_by_kind.assert_called_with("Job")
    kube_find.return_value.exists.assert_called_once()
    kube_find.return_value.delete.assert_called_once()


@pytest.mark.asyncio
async def test_install_remove_immutable_5_item(
    subprocess_shell,
    kube_get_object_by_kind,
    kube_find,
    kube_wait_for_deleted,
    helm_error_5_item,
):
    hc = helm.HelmManager()
    subprocess_shell.return_value.returncode = 1
    subprocess_shell.return_value.communicate.return_value = (
        b"",
        helm_error_5_item,
    )
    kube_find.return_value = mock.AsyncMock()
    kube_get_object_by_kind.return_value = mock.AsyncMock()

    with pytest.raises(exception.HelmImmutableFieldChange):
        await hc.run_cmd("helm upgrade --install test-release")
    assert 5 == kube_find.call_count
    expected_get_object_by_kind = [
        mock.call("Job"),
        mock.call("Job"),
        mock.call("Job"),
        mock.call("Job"),
        mock.call("Job"),
    ]
    kube_get_object_by_kind.assert_has_calls(expected_get_object_by_kind)
    expected_kube_find = [
        mock.call(mock.ANY, "cinder-bootstrap", "openstack", silent=True),
        mock.call(mock.ANY, "cinder-db-init", "openstack", silent=True),
        mock.call(
            mock.ANY,
            "cinder-drop-default-volume-type",
            "openstack",
            silent=True,
        ),
        mock.call(mock.ANY, "cinder-ks-endpoints", "openstack", silent=True),
        mock.call(mock.ANY, "cinder-ks-service", "openstack", silent=True),
    ]
    kube_find.assert_has_calls(expected_kube_find, any_order=True)
    assert 5 == kube_find.return_value.delete.call_count


@pytest.mark.asyncio
async def test_install_rollback(subprocess_shell, helm_error_rollout_restart):
    hc = helm.HelmManager()
    subprocess_shell.return_value.returncode = 1
    subprocess_shell.return_value.communicate.return_value = (
        b"",
        helm_error_rollout_restart,
    )

    with pytest.raises(exception.HelmRollback):
        await hc.run_cmd(
            "helm3 upgrade --install test-release", release_name="test-release"
        )
    subprocess_shell.assert_has_calls(
        [
            mock.call(
                "helm3 rollback test-release --namespace openstack",
                env=mock.ANY,
                stdin=mock.ANY,
                stdout=mock.ANY,
                stderr=mock.ANY,
            )
        ],
        any_order=True,
    )
