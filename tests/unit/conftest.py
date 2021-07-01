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

import asyncio
import logging
from unittest import mock

import pytest
import yaml

logging.basicConfig(level=logging.DEBUG)


# TODO(vdrok): Remove with switch to python3.8 as mock itself will be able
#              to handle async
class AsyncMock(mock.Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


@pytest.fixture
def dashboard_policy_default():
    yield yaml.safe_load(open("tests/fixtures/dashboard_policy_default.yaml"))


@pytest.fixture
def openstackdeployment():
    yield yaml.safe_load(open("tests/fixtures/openstackdeployment.yaml"))


@pytest.fixture
def common_template_args():
    yield yaml.safe_load(
        open(
            "tests/fixtures/render_service_template/input/common_template_args.yaml"
        )
    )


def _osdpl_minimal(os_release):
    return {
        "spec": {
            "openstack_version": os_release,
            "size": "tiny",
            "preset": "compute",
        }
    }


@pytest.fixture
def osdpl_min_train():
    return _osdpl_minimal("train")


@pytest.fixture
def osdpl_min_stein():
    return _osdpl_minimal("stein")


@pytest.fixture
def osdpl_min_rocky():
    return _osdpl_minimal("rocky")


@pytest.fixture
def compute_helmbundle():
    yield yaml.safe_load(open("tests/fixtures/compute_helmbundle.yaml"))


@pytest.fixture
def compute_helmbundle_all():
    yield yaml.safe_load(open("tests/fixtures/compute_helmbundle_all.yaml"))


@pytest.fixture
def kopf_adopt(mocker):
    mock_adopt = mocker.patch("kopf.adopt")
    yield mock_adopt
    mocker.stopall()


@pytest.fixture
def kubeapi(mocker):
    mock_api = mocker.patch("openstack_controller.kube.api")
    yield mock_api
    mocker.stopall()


@pytest.fixture
def kube_resource_list(mocker):
    mock_reslist = mocker.patch("openstack_controller.kube.resource_list")
    yield mock_reslist
    mocker.stopall()


@pytest.fixture
def kube_resource(mocker):
    mock_res = mocker.patch("openstack_controller.kube.resource")
    yield mock_res
    mocker.stopall()


@pytest.fixture
def asyncio_wait_for_timeout(mocker):
    async def mock_wait(f, timeout):
        await f
        raise asyncio.TimeoutError()

    mocker.patch("openstack_controller.utils.async_retry", AsyncMock())
    mock_wait = mocker.patch.object(asyncio, "wait_for", mock_wait)
    yield mock_wait
    mocker.stopall()


@pytest.fixture
def get_keystone_admin_creds(mocker):
    mock_get_creds = mocker.patch(
        "openstack_controller.openstack_utils.get_keystone_admin_creds",
        AsyncMock(return_value={"foo": "bar"}),
    )
    yield mock_get_creds
    mocker.stopall()


@pytest.fixture
def openstack_connect(mocker):
    mock_connect = mocker.patch("openstack.connect")
    yield mock_connect
    mocker.stopall()


@pytest.fixture
def override_setting(request, mocker):
    print(mocker, request.param)
    setting_mock = mocker.patch(
        f"openstack_controller.settings.{request.param['name']}",
        request.param["value"],
    )
    yield setting_mock
    mocker.stopall()
