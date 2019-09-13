import logging

import pytest
import yaml

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def openstackdeployment():
    yield yaml.safe_load(open("tests/fixtures/openstackdeployment.yaml"))


@pytest.fixture
def compute_helmbundle():
    yield yaml.safe_load(open("tests/fixtures/compute_helmbundle.yaml"))


@pytest.fixture
def kubeapi(mocker):
    mock_api = mocker.patch("osh_operator.kube.api")
    yield mock_api
    mocker.stopall()


@pytest.fixture
def credentials(mocker):
    creds = mocker.patch("osh_operator.openstack.get_or_create_os_credentials")
    yield creds
    mocker.stopall()
