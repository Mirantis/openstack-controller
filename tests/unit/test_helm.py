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
async def test_get_reelase_values(subprocess_shell, release_values):
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
