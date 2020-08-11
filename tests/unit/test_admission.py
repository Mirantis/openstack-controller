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
                "profile": "compute",
                "size": "tiny",
                "features": {
                    "neutron": {
                        "floating_network": {
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
    req["request"]["object"]["spec"]["features"]["neutron"] = {}

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
    req["request"]["object"]["spec"]["features"]["neutron"] = {}
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is False
    assert response.json["response"]["status"]["code"] == 400
    assert (
        "physnet needs to be specified"
        in response.json["response"]["status"]["message"]
    )


def test_physnet_optional_tf(client):
    req = copy.deepcopy(ADMISSION_REQ)
    req["request"]["object"]["spec"]["features"]["neutron"] = {
        "backend": "tungstenfabric"
    }
    response = client.simulate_post("/validate", json=req)
    assert response.status == falcon.HTTP_OK
    assert response.json["response"]["allowed"] is True
