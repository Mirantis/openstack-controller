# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import json

import falcon
from falcon import testing
import pytest

from openstack_controller.admission import controller


# https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#request
ADMISSION_REQ_JSON = """
{
    "apiVersion": "admission.k8s.io/v1",
    "kind": "AdmissionReview",
    "request": {
        "uid": "00000000-0000-0000-0000-000000000000",
        "kind": {
            "group": "lcm.mirantis.com",
            "version": "v1alpha1",
            "kind": "OpenStackDeployment"
        },
        "resource": {
            "group": "lcm.mirantis.com",
            "version": "v1alpha1",
            "resource": "openstackdeployments"
        },
        "name": "osh-dev",
        "namespace": "openstack",
        "operation": "CREATE",
        "object": {
            "apiVersion": "lcm.mirantis.com/v1alpha1",
            "kind": "OpenStackDeployment",
            "spec": {
                "openstack_version": "ussuri",
                "preset": "compute",
                "size": "tiny",
                "features": {
                    "services": [
                       "key-manager",
                       "object-storage"
                    ],
                    "neutron": {
                        "floating_network": {
                            "enabled": true,
                            "physnet": "physnet1"
                        }
                    }
                }
            }
        },
        "oldObject": null,
        "dryRun": false
    }
}
"""

ADMISSION_REQ = json.loads(ADMISSION_REQ_JSON)


@pytest.fixture
def client():
    return testing.TestClient(controller.create_api())


def test_root(client):
    response = client.simulate_get("/")
    assert response.status == falcon.HTTP_OK


def test_minimal_validation_response(client):
    req = copy.deepcopy(ADMISSION_REQ)
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_validate_invalid_request_body(client):
    req = "Boo!"
    response = client.simulate_post("/validate", body=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Exception parsing the body of request: Expecting value"
        in response.json["response"]["status"]["message"]
    )


def test_validate_not_satisfying_schema(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req.pop("apiVersion")
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "'apiVersion' is a required property"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_create_master_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["openstack_version"] = "master"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Using master of OpenStack is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_upgrade_ok(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["oldObject"]["spec"]["openstack_version"] = "train"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_openstack_upgrade_to_master_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["object"]["spec"]["openstack_version"] = "master"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Using master of OpenStack is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_validator_single_fail(client):
    """Test that validation stops on first error"""
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    # set up for both master failure and neutron physnet required failure
    # openstack check must be called first and only its failure returned
    req["request"]["object"]["spec"]["openstack_version"] = "master"
    req["request"]["object"]["spec"]["features"]["neutron"][
        "floating_network"
    ] = {"enabled": True}
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Using master of OpenStack is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_skiplevel_upgrade_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["oldObject"]["spec"]["openstack_version"] = "stein"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "Skip-level OpenStack version upgrade is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_openstack_downgrade_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["object"]["spec"]["openstack_version"] = "train"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "downgrade is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_upgrade_with_extra_changes_fail(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["operation"] = "UPDATE"
    req["request"]["oldObject"] = copy.deepcopy(req["request"]["object"])
    req["request"]["oldObject"]["spec"]["openstack_version"] = "train"
    req["request"]["object"]["spec"]["size"] = "small"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "changing other values in the spec is not permitted"
        in response.json["response"]["status"]["message"]
    )


def test_physnet_required_no_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["neutron"][
        "floating_network"
    ] = {"enabled": True}
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "physnet needs to be specified"
        in response.json["response"]["status"]["message"]
    )


def test_instance_ha_allow_in_services(client):
    allow_in = ["ussuri", "victoria"]
    for os_version in allow_in:
        req = copy.deepcopy(ADMISSION_REQ)
        req["request"]["object"]["spec"]["openstack_version"] = os_version
        req["request"]["object"]["spec"]["features"]["services"].append(
            "instance-ha"
        )
        response = client.simulate_post("/validate", json=req)
        assert response.status == falcon.HTTP_OK
        assert response.json["response"]["allowed"] is True


def test_insance_ha_deny_in_services(client):
    deny_in = ["queens", "rocky", "stein", "train"]
    for os_version in deny_in:
        req = copy.deepcopy(ADMISSION_REQ)
        req["request"]["object"]["spec"]["openstack_version"] = os_version
        req["request"]["object"]["spec"]["features"]["services"].append(
            "instance-ha"
        )
        response = client.simulate_post("/validate", json=req)
        assert response.status == falcon.HTTP_OK
        assert response.json["response"]["allowed"] is False
        assert response.json["response"]["status"]["code"] == 400


def test_physnet_optional_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["preset"] = "compute-tf"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_ipsec_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"].update(
        {
            "preset": "compute-tf",
            "features": {"neutron": {"ipsec": {"enabled": True}}},
        }
    )
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400


def test_baremetal_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["preset"] = "compute-tf"
    req["request"]["object"]["spec"]["features"]["services"].append(
        "baremetal"
    )
    req["request"]["object"]["spec"]["features"]["ironic"] = {"test": "test"}
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False


def test_baremetal_ovs(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["preset"] = "compute"
    req["request"]["object"]["spec"]["features"]["services"].append(
        "baremetal"
    )
    req["request"]["object"]["spec"]["features"]["ironic"] = {"test": "test"}
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_baremetal_empty_config(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["preset"] = "compute"
    req["request"]["object"]["spec"]["features"]["services"].append(
        "baremetal"
    )
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False


def test_baremetal_non_empty_config(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["preset"] = "compute"
    req["request"]["object"]["spec"]["features"]["services"].append(
        "baremetal"
    )
    req["request"]["object"]["spec"]["features"]["ironic"] = {"test": "test"}
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_bgpvpn_peers(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"].update(
        {
            "preset": "compute",
            "features": {
                "neutron": {"bgpvpn": {"enabled": True, "peers": ["1.2.3.4"]}}
            },
        }
    )
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_bgpvpn_route_reflector_enabled(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"].update(
        {
            "preset": "compute",
            "features": {
                "neutron": {
                    "bgpvpn": {
                        "enabled": True,
                        "route_reflector": {"enabled": True},
                    }
                }
            },
        }
    )
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_bgpvpn_route_reflector_disabled_no_peers(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"].update(
        {
            "preset": "compute",
            "features": {
                "neutron": {
                    "bgpvpn": {
                        "enabled": True,
                        "route_reflector": {"enabled": False},
                    }
                }
            },
        }
    )
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400


def test_bgpvpn_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"].update(
        {
            "preset": "compute-tf",
            "features": {
                "neutron": {"bgpvpn": {"enabled": True, "peers": ["1.2.3.4"]}}
            },
        }
    )
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400


def test_nova_encryption(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["nova"] = {
        "images": {"backend": "local", "encryption": {"enabled": False}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True

    req["request"]["object"]["spec"]["features"]["nova"] = {
        "images": {"backend": "local", "encryption": {"enabled": True}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False

    req["request"]["object"]["spec"]["features"]["nova"] = {
        "images": {"backend": "lvm", "encryption": {"enabled": True}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True

    req["request"]["object"]["spec"]["features"]["nova"] = {
        "images": {"backend": "lvm", "encryption": {"enabled": False}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def _node_specific_request(client, node_override, result):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["nodes"] = node_override
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    if result:
        assert response.json["response"]["allowed"]
    else:
        assert response.json["response"]["allowed"] is False


def test_nodes_node_label(client):
    _node_specific_request(client, {"wrong:label": {"features": {}}}, False)
    _node_specific_request(client, {"good::label": {"services": {}}}, True)


def test_nodes_top_keys(client):
    allowed_top_keys = ["services", "features"]
    for top_key in allowed_top_keys:
        _node_specific_request(client, {"good::label": {top_key: {}}}, True)
    _node_specific_request(client, {"good::label": {"fake": {}}}, False)


def test_nodes_allowed_keys(client):
    allowed_value_override = {"chart_daemonset": {"values": {"conf": {}}}}
    allowed_services = [
        {
            "load-balancer": {"octavia": allowed_value_override},
        },
        {
            "networking": {
                "neutron": allowed_value_override,
                "openvswitch": allowed_value_override,
            }
        },
        {"metering": {"ceilometer": allowed_value_override}},
        {"metric": {"gnocchi": allowed_value_override}},
        {"compute": {"nova": allowed_value_override}},
    ]
    for service in allowed_services:
        _node_specific_request(
            client,
            {"good::label": {"services": service}},
            True,
        )


def test_nodes_wrong_key(client):
    allowed_value_override = {"chart_daemonset": {"values": {"conf": {}}}}
    wrong_service = {
        "identity": {"keystone": allowed_value_override},
    }
    _node_specific_request(
        client,
        {"good::label": {"services": wrong_service}},
        False,
    )


def test_nodes_wrong_chart_value_key(client):
    wrong_value_override = {"chart_daemonset": {"wrong": {"conf": {}}}}
    allowed_service = {
        "compute": {"nova": wrong_value_override},
    }
    _node_specific_request(
        client,
        {"good::label": {"services": allowed_service}},
        False,
    )


def test_nodes_features_top_keys(client):
    allowed_top_keys = [("neutron", {}), ("nova", {})]
    for top_key, top_value in allowed_top_keys:
        _node_specific_request(
            client, {"good::label": {"features": {top_key: {}}}}, True
        )
    _node_specific_request(
        client, {"good::label": {"features": {"fake": {}}}}, False
    )


def test_nodes_features_nova_keys(client):
    # Images valid
    for backend in ["lvm", "ceph", "local"]:
        _node_specific_request(
            client,
            {
                "good::label": {
                    "features": {
                        "nova": {
                            "images": {
                                "backend": backend,
                            }
                        }
                    }
                }
            },
            True,
        )

    # Images invalid
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "nova": {
                        "images": {
                            "backend": "invalid",
                        }
                    }
                }
            }
        },
        False,
    )

    # Encryption
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "nova": {
                        "images": {
                            "encryption": {"enabled": True},
                        }
                    }
                }
            }
        },
        True,
    )

    # live_migration interface
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {"nova": {"live_migration_interface": "live01"}}
            }
        },
        True,
    )


def test_nodes_features_neutron_keys(client):
    neutron_required = {"dpdk": {"enabled": True, "driver": "igb_uio"}}
    _node_specific_request(
        client,
        {"good::label": {"features": {"neutron": neutron_required}}},
        True,
    )

    # Bridges valid
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bridges": [
                                {"name": "br1", "ip_address": "1.2.3.4/24"}
                            ],
                        }
                    }
                }
            }
        },
        True,
    )

    # Bridges valid additional fields
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bridges": [
                                {
                                    "name": "br1",
                                    "ip_address": "1.2.3.4/24",
                                    "additional": "",
                                }
                            ],
                        }
                    }
                }
            }
        },
        True,
    )

    # Bridges missing IP
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bridges": [{"name": "br1"}],
                        }
                    }
                }
            }
        },
        False,
    )

    # Bonds valid
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bonds": [
                                {
                                    "name": "foo",
                                    "bridge": "br1",
                                    "nics": [
                                        {"name": "br1", "pci_id": "1.2.3:00.1"}
                                    ],
                                }
                            ],
                        }
                    }
                }
            }
        },
        True,
    )

    # Bonds valid additional fields
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bonds": [
                                {
                                    "name": "foo",
                                    "bridge": "br1",
                                    "nics": [
                                        {
                                            "name": "br1",
                                            "pci_id": "1.2.3:00.1",
                                            "additional": "option",
                                        }
                                    ],
                                }
                            ],
                        },
                        "tunnel_interface": "br-phy",
                    }
                }
            }
        },
        True,
    )

    # Bonds Missing PCI_ID
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "dpdk": {
                            "enabled": True,
                            "driver": "igb_uio",
                            "bonds": [
                                {
                                    "name": "foo",
                                    "bridge": "br1",
                                    "nics": [{"name": "br1"}],
                                }
                            ],
                        }
                    }
                }
            }
        },
        False,
    )


def test_nodes_features_neutron_sriov_keys(client):
    neutron_required = {"sriov": {"enabled": True}}
    _node_specific_request(
        client,
        {"good::label": {"features": {"neutron": neutron_required}}},
        True,
    )
    # nics valid
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "sriov": {
                            "enabled": True,
                            "nics": [
                                {
                                    "device": "enp1",
                                    "num_vfs": 32,
                                    "physnet": "tenant",
                                }
                            ],
                        }
                    }
                }
            }
        },
        True,
    )
    # nics valid additional fields
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "sriov": {
                            "enabled": True,
                            "nics": [
                                {
                                    "device": "enp1",
                                    "num_vfs": 32,
                                    "hooks": {"init": "echo 'Init hook'"},
                                    "physnet": "tenant",
                                    "mtu": 1500,
                                }
                            ],
                        }
                    }
                }
            }
        },
        True,
    )
    # NICS missing num_vfs
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "neutron": {
                        "sriov": {
                            "enabled": True,
                            "nics": [
                                {
                                    "device": "enp1",
                                    "physnet": "tenant",
                                }
                            ],
                        }
                    }
                }
            }
        },
        False,
    )


def test_nodes_features_cinder_keys(client):
    cinder_required = {
        "volume": {"backends": {"lvm_backend": {"lvm": {"option": "value"}}}}
    }
    _node_specific_request(
        client,
        {"good::label": {"features": {"cinder": cinder_required}}},
        True,
    )
    # backend valid
    _node_specific_request(
        client,
        {
            "good::label": {
                "features": {
                    "cinder": {
                        "volume": {
                            "backends": {
                                "lvm_fast": {
                                    "lvm": {"foo": "bar"},
                                },
                                "lvm_slow": {
                                    "lvm": {"foo": "baz"},
                                },
                            }
                        }
                    }
                }
            }
        },
        True,
    )


def test_glance_signature(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["glance"] = {
        "signature": {"enabled": True}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True

    req["request"]["object"]["spec"]["features"]["glance"] = {
        "signature": {"enabled": True, "certificate_validation": True}
    }

    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True

    req["request"]["object"]["spec"]["features"]["glance"] = {
        "signature": {"enabled": False, "certificate_validation": True}
    }

    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400


def test_glance_features_cinder_keys(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {
            "cinder": {
                "backend1": {"default": True, "backend_name": "lvm:fast"}
            }
        }
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True

    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {
            "cinder": {
                "backend1": {"default": True, "cinder_volume_type": "fast"}
            }
        }
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_glance_features_multiple_backends_ok(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {
            "cinder": {
                "backend1": {"default": True, "backend_name": "lvm:fast"},
                "backend2": {"backend_name": "lvm:fast"},
            }
        }
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True


def test_glance_features_multiple_defaults(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {
            "cinder": {
                "backend1": {"default": True, "backend_name": "lvm:fast"},
                "backend2": {"default": True, "backend_name": "lvm:fast"},
            }
        }
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400


def test_glance_features_cinder_missing_mandatory(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {"cinder": {"backend1": {"backend_name": "lvm:fast"}}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False

    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {"cinder": {"backend1": {"default": True}}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False

    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {"cinder": {"backend1": {"default": True}}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False


def test_glance_features_cinder_invalid_backend_name(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {
            "cinder": {
                "backend1": {"default": True, "backend_name": "lvmfast"}
            }
        }
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False


def test_glance_features_cinder_missing_default(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["glance"] = {
        "backends": {"cinder": {"backend1": {"backend_name": "lvm:fast"}}}
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False


def test_barbican_features_namespace_before_victoria(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["barbican"] = {
        "backends": {"vault": {"enabled": True, "namespace": "spam"}}
    }
    req["request"]["object"]["spec"]["openstack_version"] = "ussuri"
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["status"]["code"] == 400
    assert response.json["response"]["allowed"] is False
