import copy
import json
import logging
from unittest import mock

import kopf
import pytest

from openstack_controller import layers


CREDS_KWARGS = {
    "ssh_credentials": {"private": "", "public": ""},
    "credentials": {
        "memcached": "",
        "database": {"user": {"username": "", "password": ""}},
        "messaging": {"user": {"username": "", "password": ""}},
        "notifications": {"user": {"username": "", "password": ""}},
    },
    "admin_creds": {
        "database": {"username": "", "password": ""},
        "identity": {"password": "", "username": ""},
        "messaging": {"password": "", "username": ""},
    },
    "ceph": {
        "nova": {"username": "", "secrets": "", "keyring": "", "pools": {}}
    },
}


def test_apply_list_empty_stein(osdpl_min_stein):
    compute_services = {
        "block-storage",
        "compute",
        "dns",
        "placement",
        "identity",
        "dashboard",
        "image",
        "ingress",
        "database",
        "memcached",
        "networking",
        "orchestration",
        "messaging",
        "load-balancer",
        "coordination",
        "key-manager",
        "redis",
    }
    ta, td = layers.services(osdpl_min_stein["spec"], mock.Mock())
    assert ta == compute_services
    assert not td


def test_apply_list_empty_train(osdpl_min_train):
    compute_services = {
        "block-storage",
        "compute",
        "dns",
        "placement",
        "identity",
        "dashboard",
        "image",
        "ingress",
        "database",
        "memcached",
        "networking",
        "orchestration",
        "messaging",
        "load-balancer",
        "coordination",
        "key-manager",
        "redis",
    }
    ta, td = layers.services(osdpl_min_train["spec"], mock.Mock())
    assert ta == compute_services
    assert not td


def test_apply_list_empty_rocky(osdpl_min_rocky):
    compute_services = {
        "block-storage",
        "compute",
        "dns",
        "identity",
        "dashboard",
        "image",
        "ingress",
        "database",
        "memcached",
        "networking",
        "orchestration",
        "messaging",
        "load-balancer",
        "coordination",
        "key-manager",
        "redis",
    }
    ta, td = layers.services(osdpl_min_rocky["spec"], mock.Mock())
    assert ta == compute_services
    assert not td


def test_apply_list_not_empty(openstackdeployment):
    ta, td = layers.services(openstackdeployment["spec"], mock.Mock())
    assert "compute" in ta
    assert not td


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
    images_mock = mock.Mock()
    images_mock = ["a", "b"]
    data = layers.render_service_template(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        openstackdeployment["spec"],
        logging,
        credentials=mock.Mock(),
        admin_creds=mock.Mock(),
        images=images_mock,
        ceph={
            "nova": {
                "pools": {},
                "username": "nova",
                "keyring": "nova",
                "secrets": "nova",
            }
        },
        ssh_credentials={
            "private": "nova_private_key",
            "public": "nova_public_key",
        },
    )
    assert len(data) == 1 and "spec" in data


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
    # this overrides are for nova only
    # as rabbitmq and libvirt are not in openstack group
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
    # helmbundle values will be overriden by common.chart.releases
    # for all charts
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


@mock.patch.object(layers, "render_service_template")
def test_merge_all_type_conflict(rst, openstackdeployment, compute_helmbundle):
    openstackdeployment["spec"]["services"]["compute"]["nova"]["values"][
        "conf"
    ] = {"ceph": {"enabled": None}}
    rst.return_value = compute_helmbundle
    with pytest.raises(kopf.PermanentError, match="conf:ceph:enabled"):
        layers.merge_all_layers(
            "compute",
            openstackdeployment,
            openstackdeployment["metadata"],
            openstackdeployment["spec"],
            logging,
        )


@mock.patch.object(layers, "LOG")
def test_merge_all_float_int(
    mock_log, openstackdeployment, compute_helmbundle
):
    spec = copy.deepcopy(openstackdeployment["spec"])
    openstackdeployment["spec"]["common"]["charts"]["releases"]["values"] = {
        "conf": {"nova": {"scheduler": {"ram_weight_multiplier": 1.0}}}
    }
    openstackdeployment["spec"]["services"]["compute"]["nova"]["values"][
        "conf"
    ] = {"nova": {"scheduler": {"ram_weight_multiplier": 2}}}
    helmbundle = layers.merge_all_layers(
        "compute",
        openstackdeployment,
        openstackdeployment["metadata"],
        spec,
        logging,
        **CREDS_KWARGS,
    )
    assert (
        helmbundle["spec"]["releases"][2]["values"]["conf"]["nova"][
            "scheduler"
        ]["ram_weight_multiplier"]
        == 2
    )
    mock_log.assert_not_called()


def test_spec_hash():
    obj1 = """{
"spec": {
  "foo": {
    "bar": "baz",
    "eggs": {
        "parrots": "vikings",
        "ham": "spam"
        }
    },
  "fools": [1,2]
 }
}
 """
    # change order of keys in spec, change order of keys overall,
    # change values in keys other that spec
    # spec_hash should be the same
    obj2 = """{
"spec": {
  "fools": [1,2],
  "foo": {
    "eggs": {
        "ham": "spam",
        "parrots": "vikings"
        },
    "bar": "baz"
    }
 }
 }
"""
    assert layers.spec_hash(json.loads(obj1)) == layers.spec_hash(
        json.loads(obj2)
    )


def test_merge_all_two_layers():
    meta = {}
    spec = {
        "openstack_version": "master",
        "artifacts": {"images_base_url": "", "binary_base_url": ""},
        "common": {"charts": {"repositories": ""}, "openstack": {"repo": ""}},
        "features": {
            "ssl": {
                "public_endpoints": {
                    "ca_cert": "",
                    "api_cert": "",
                    "api_key": "",
                }
            }
        },
    }

    osdpl = {"spec": spec}
    logger = mock.MagicMock()
    # test layer 1 service values are overriden by layer 2 common values
    l1 = copy.deepcopy(spec)
    l2 = copy.deepcopy(osdpl)
    l1["services"] = {"placement": {"placement": {"values": {"a": 1}}}}
    l2["spec"]["common"]["charts"]["releases"] = {"values": {"a": 2}}
    helmbundle = layers.merge_all_layers(
        "placement", l2, meta, l1, logger, **CREDS_KWARGS
    )
    assert helmbundle["spec"]["releases"][0]["values"]["a"] == 2
    # test layer 1 service values are overriden by layer 2 service values
    l1 = copy.deepcopy(spec)
    l2 = copy.deepcopy(osdpl)
    l1["services"] = {"placement": {"placement": {"values": {"b": 1}}}}
    l2["spec"]["services"] = {"placement": {"placement": {"values": {"b": 2}}}}
    helmbundle = layers.merge_all_layers(
        "placement", l2, meta, l1, logger, **CREDS_KWARGS
    )
    assert helmbundle["spec"]["releases"][0]["values"]["b"] == 2
    # test layer 1 service values are used
    l1 = copy.deepcopy(spec)
    l2 = copy.deepcopy(osdpl)
    l1["services"] = {"placement": {"placement": {"values": {"c": 1}}}}
    helmbundle = layers.merge_all_layers(
        "placement", l2, meta, l1, logger, **CREDS_KWARGS
    )
    assert helmbundle["spec"]["releases"][0]["values"]["c"] == 1
    # test layer 2 service values are used
    l1 = copy.deepcopy(spec)
    l2 = copy.deepcopy(osdpl)
    l2["spec"]["services"] = {"placement": {"placement": {"values": {"d": 1}}}}
    helmbundle = layers.merge_all_layers(
        "placement", l2, meta, l1, logger, **CREDS_KWARGS
    )
    assert helmbundle["spec"]["releases"][0]["values"]["d"] == 1


def test_merge_list_with_duplicates():
    merger = layers.merger
    l = [
        {
            "conf": {
                "nova": {
                    "DEFAULT": {
                        "passthrough_whitelist": '[{ "devname": "enp5s0f2", "physical_network": "physnet2"}]'
                    }
                }
            },
            "label": {"key": "devname", "values": ["enp5s0f1"]},
        }
    ]
    new_list = merger.merge(l, copy.deepcopy(l))
    assert new_list == l
