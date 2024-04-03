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
from openstack_controller import kube
from openstack_controller import layers
from openstack_controller import resource_view

import pytest
import yaml

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)


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


def render_mspec():
    osdpl = yaml.safe_load(open("tests/fixtures/openstackdeployment.yaml"))
    mspec = layers.merge_spec(osdpl["spec"], LOG)
    # Set explicit version for tests
    mspec["common"]["openstack"]["releases"]["version"] = "0.1.0-os-0"
    mspec["common"]["infra"]["releases"]["version"] = "0.1.0-infra-0"
    return mspec


@pytest.fixture
def openstackdeployment_mspec():
    return render_mspec()


@pytest.fixture
def common_template_args():
    yield yaml.safe_load(
        open(
            "tests/fixtures/render_service_template/input/common_template_args.yaml"
        )
    )


def _osdpl_minimal(os_release):
    return {
        "openstack_version": os_release,
        "size": "tiny",
        "preset": "compute",
    }


def _osdpl_mspec(os_release):
    osdpl = _osdpl_minimal(os_release)
    mspec = layers.merge_spec(osdpl, LOG)
    return mspec


@pytest.fixture
def osdpl_min_train():
    return _osdpl_mspec("train")


@pytest.fixture
def osdpl_min_stein():
    return _osdpl_mspec("stein")


@pytest.fixture
def osdpl_min_rocky():
    return _osdpl_mspec("rocky")


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
    mock_api = mocker.patch("openstack_controller.kube.KUBE_API")
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


@pytest.fixture
def fake_osdpl(openstackdeployment):
    osdpl = kube.OpenStackDeployment(kube.kube_client(), openstackdeployment)
    yield osdpl


@pytest.fixture
def load_fixture():
    def loader(name):
        return yaml.safe_load(open("tests/fixtures/" + name))

    yield loader


@pytest.fixture
def helm_error_1_item():
    fixture_file = "tests/fixtures/test_helm/1_item.txt"
    with open(fixture_file, "rb") as f:
        error = f.read()
    yield error


@pytest.fixture
def helm_error_5_item():
    fixture_file = "tests/fixtures/test_helm/5_item.txt"
    with open(fixture_file, "rb") as f:
        error = f.read()
    yield error


@pytest.fixture
def helm_error_forbidden_item():
    fixture_file = "tests/fixtures/test_helm/forbidden_item.txt"
    with open(fixture_file, "rb") as f:
        error = f.read()
    yield error


@pytest.fixture
def helm_error_rollout_restart():
    fixture_file = "tests/fixtures/test_helm/rollout_restart.txt"
    with open(fixture_file, "rb") as f:
        error = f.read()
    yield error


@pytest.fixture
def substitute_mock(mocker):
    substitute_mock = mocker.patch(
        f"openstack_controller.layers.substitude_osdpl",
    )
    yield substitute_mock
    mocker.stopall()


@pytest.fixture
def helm_error_pvc_test():
    fixture_file = "tests/fixtures/test_helm/pvc_test.txt"
    with open(fixture_file, "rb") as f:
        error = f.read()
    yield error


@pytest.fixture(scope="session")
def child_view():
    mspec = render_mspec()
    return resource_view.ChildObjectView(mspec)


@pytest.fixture
def node(mocker):
    node = mocker.patch("openstack_controller.kube.Node")
    node.return_value = mock.MagicMock()
    node.return_value.name = "fake-node"
    yield node.return_value
    mocker.stopall()


@pytest.fixture
def safe_node(mocker):
    node = mocker.patch("openstack_controller.kube.safe_get_node")
    node.return_value = mock.MagicMock()
    node.return_value.name = "fake-node"
    yield node.return_value
    mocker.stopall()


@pytest.fixture
def nwl(mocker):
    nwl = mocker.patch(
        "openstack_controller.maintenance.NodeWorkloadLock.get_by_node"
    )
    nwl.reteurn_value = mock.Mock()
    yield nwl
    mocker.stopall()


@pytest.fixture
def socket(mocker):
    nwl = mocker.patch("socket.socket")
    nwl.reteurn_value = mock.Mock()
    yield nwl
    mocker.stopall()
