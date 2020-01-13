import logging

import pytest
import yaml

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def openstackdeployment():
    yield yaml.safe_load(open("tests/fixtures/openstackdeployment.yaml"))


def _osdpl_minimal(os_release):
    return {
        "spec": {
            "openstack_version": os_release,
            "size": "tiny",
            "profile": "compute",
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
def kubeapi(mocker):
    mock_api = mocker.patch("openstack_controller.kube.api")
    yield mock_api
    mocker.stopall()


@pytest.fixture
def credentials(mocker):
    creds = mocker.patch(
        "openstack_controller.openstack.get_or_create_os_credentials"
    )
    yield creds
    mocker.stopall()


@pytest.fixture
def service_credentials(mocker):
    creds = mocker.patch(
        "openstack_controller.secrets.get_or_create_service_credentials"
    )
    yield creds
    mocker.stopall()
