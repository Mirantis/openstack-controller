import copy
import logging
from unittest import mock

import pytest
import yaml

from osh_operator import layers
from osh_operator import openstack


@pytest.fixture
def openstackdeployment():
    yield yaml.safe_load(open("tests/fixtures/openstackdeployment.yaml"))


@pytest.fixture
def compute_helmbundle():
    yield yaml.safe_load(open("tests/fixtures/compute_helmbundle.yaml"))


def test_no_changes_for_empty_services():
    ta, td = layers.services({}, mock.Mock())
    assert not ta
    assert not td


def test_apply_list_not_empty(openstackdeployment):
    ta, td = layers.services(openstackdeployment["spec"], mock.Mock())
    assert "compute" in ta
    assert not td


def test_delete_list_not_empty():
    diff = [
        ("add", ("metadata", "labels", "label1"), None, "new-value"),
        ("change", ("metadata", "labels", "label2"), "old-value", "new-value"),
        ("remove", ("metadata", "labels", "label3"), "old-value", None),
        ("change", ("spec", "size"), "10G", "100G"),
        (
            "change",
            ("spec", "features", "services"),
            ("compute", "image"),
            ("compute",),
        ),
    ]
    # TODO(avolkov): check "remove" op has the same semantic
    # regarding old/new values
    ta, td = layers.services({}, logging, diff=diff)
    assert not ta
    assert "image" in td


def test_fail_render_template_with_incorrect_release(openstackdeployment):
    openstackdeployment["spec"]["openstack_version"] = "fake"
    render = lambda: layers.render_service_template(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        openstackdeployment["spec"],
        logging,
    )
    pytest.raises(Exception, render, match="Template not found")


def test_render_template(openstackdeployment):
    data = layers.render_service_template(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        openstackdeployment["spec"],
        logging,
        credentials=mock.Mock(),
    )
    assert data["metadata"]["name"] == "openstack-compute"


@mock.patch.object(layers, "render_service_template")
def test_merge_all_no_modification(
    rst, openstackdeployment, compute_helmbundle
):
    compute_helmbundle["spec"]["repositories"] = []
    openstackdeployment["spec"]["common"]["charts"]["repositories"] = []

    # nullify merge points for openstackdeployment
    openstackdeployment["spec"]["common"]["charts"]["releases"] = {}
    openstackdeployment["spec"]["common"]["openstack"]["values"] = {}
    openstackdeployment["spec"]["common"]["openstack"]["releases"] = {}
    openstackdeployment["spec"]["services"]["compute"] = {}

    rst.return_value = compute_helmbundle
    compute_helmbundle = copy.deepcopy(compute_helmbundle)
    result = layers.merge_all_layers(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        openstackdeployment["spec"],
        logging,
    )
    assert id(result) != id(compute_helmbundle)
    assert result == compute_helmbundle


@mock.patch.object(layers, "render_service_template")
def test_merge_all_prioritize_service_values_over_common_group_values(
    rst, openstackdeployment, compute_helmbundle
):
    # let's nova chart has some config values
    compute_helmbundle["spec"]["releases"][2]["values"] = {"test0": 0}
    # and others charts are empty
    for i in range(2):
        compute_helmbundle["spec"]["releases"][i]["values"] = {}
    rst.return_value = compute_helmbundle

    openstackdeployment["spec"]["common"]["charts"]["repositories"] = []
    openstackdeployment["spec"]["common"]["charts"]["releases"]["values"] = {}
    # this overrides are for nova only as rabbitmq and libvirt are not in openstack group
    openstackdeployment["spec"]["common"]["openstack"]["values"] = {
        "test1": 1,
        "test2": 2,
    }
    openstackdeployment["spec"]["services"]["compute"]["nova"]["values"] = {
        "test2": 3,
        "test3": 4,
    }
    result = layers.merge_all_layers(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        openstackdeployment["spec"],
        logging,
    )
    # rabbitmq and libvirt
    for i in range(2):
        assert result["spec"]["releases"][i]["values"] == {}
    # nova
    assert result["spec"]["releases"][2]["values"] == {
        "test0": 0,
        "test1": 1,
        "test2": 3,
        "test3": 4,
    }


@mock.patch.object(layers, "render_service_template")
def test_merge_all_prioritize_group_releases_over_chart_releases(
    rst, openstackdeployment, compute_helmbundle
):
    # let's nova chart has some config values
    compute_helmbundle["spec"]["releases"][2]["values"] = {"test0": 0}
    # and others charts are empty
    for i in range(2):
        compute_helmbundle["spec"]["releases"][i]["values"] = {}
    rst.return_value = compute_helmbundle

    openstackdeployment["spec"]["common"]["charts"]["repositories"] = []
    openstackdeployment["spec"]["common"]["charts"]["releases"]["values"] = {}
    openstackdeployment["spec"]["services"]["compute"] = {}
    # helmbundle values will be overriden by common.chart.releases for all charts
    openstackdeployment["spec"]["common"]["charts"]["releases"]["values"] = {
        "test1": 1,
        "test2": 2,
    }
    # and then overrides for nova only
    openstackdeployment["spec"]["common"]["openstack"] = {
        "releases": {"values": {"test2": 3, "test3": 4}}
    }
    result = layers.merge_all_layers(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        openstackdeployment["spec"],
        logging,
    )
    # rabbitmq and libvirt
    for i in range(2):
        assert result["spec"]["releases"][i]["values"] == {
            "test1": 1,
            "test2": 2,
        }
    # nova
    assert result["spec"]["releases"][2]["values"] == {
        "test0": 0,
        "test1": 1,
        "test2": 3,
        "test3": 4,
    }


@mock.patch.object(openstack, "get_or_create_os_credentials")
def test_render_all(mock_creds, openstackdeployment):
    openstackdeployment_old = copy.deepcopy(openstackdeployment)
    compute_helmbundle = layers.render_all(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        openstackdeployment["spec"],
        logging,
    )

    mock_creds.assert_called_once_with("compute", "openstack")
    # check no modification in-place for openstackdeployment
    assert openstackdeployment_old == openstackdeployment
    assert compute_helmbundle["metadata"]["name"] == "openstack-compute"
    # check helmbundle has data from base.yaml
    assert compute_helmbundle["spec"]["releases"][0]["values"]["images"][
        "tags"
    ]
