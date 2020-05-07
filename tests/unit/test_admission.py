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
import io
import json
import unittest
from unittest import mock

from openstack_controller.admission import controller
from openstack_controller.admission.validators import base
from openstack_controller.admission.validators import openstack as osv
from openstack_controller.admission.validators import neutron
from openstack_controller import exception


REQ_BODY_DICT = {
    "apiVersion": "admission.k8s.io/v1beta1",
    "kind": "AdmissionReview",
    "request": {
        "uid": "705ab4f5-6393-11e8-b7cc-42010a800002",
        "kind": {
            "group": "lcm.mirantis.com",
            "version": "v1alpha1",
            "kind": "OpenStackDeployment",
        },
        "object": {"spec": {"features": {"services": []}}},
    },
}

TEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-03/schema#",
    "type": "object",
    "properties": {"apiVersion": {"type": "string", "required": True}},
    "additionalProperties": True,
}


class OkValidator(base.BaseValidator):
    def validate(self, review_request):
        pass


class FailValidator(base.BaseValidator):
    def validate(self, review_request):
        raise exception.OsDplValidationFailed("VIKINGS!")


FAKE_VALIDATORS = {
    "openstack": OkValidator(),
    "ok": OkValidator(),
    "fail": FailValidator(),
}

FAKE_SERVICES = ({"ok", "fail"}, set())


class TestRootController(unittest.TestCase):
    def setUp(self):
        self.controller = controller.RootResource()

    def test_root(self):
        self.controller.on_get(None, None)


@mock.patch.object(controller, "_load_schema", TEST_SCHEMA)
class TestValidationController(unittest.TestCase):
    def setUp(self):
        self.req_body_dict = copy.deepcopy(REQ_BODY_DICT)
        self.resp = mock.MagicMock(body="")
        self.controller = controller.ValidationResource()

    def test_validate_invalid_request_body(self):
        req = mock.MagicMock(stream=io.StringIO("boo"))
        self.controller.on_post(req, self.resp)
        self.assertIn("400", self.resp.body)
        self.assertIn(
            "Exception parsing the body of request: Expecting value",
            self.resp.body,
        )

    def test_validate_not_satisfying_schema(self):
        self.req_body_dict.pop("apiVersion")
        req_body = json.dumps(self.req_body_dict)
        req = mock.MagicMock(stream=io.StringIO(req_body))
        self.controller.on_post(req, self.resp)
        self.assertIn("400", self.resp.body)
        self.assertIn("'apiVersion' is a required property", self.resp.body)

    @mock.patch.object(
        FAKE_VALIDATORS["ok"], "validate",
    )
    @mock.patch.object(
        FAKE_VALIDATORS["fail"],
        "validate",
        wraps=FAKE_VALIDATORS["fail"].validate,
    )
    @mock.patch.object(controller, "_VALIDATORS", FAKE_VALIDATORS)
    @mock.patch.object(
        controller.layers, "services", return_value=FAKE_SERVICES
    )
    def test_validate_validators_stop_after_first_fail(
        self, svc_mock, fail_mock, ok_mock
    ):
        ok_mock.side_effect = exception.OsDplValidationFailed("VIKINGS!")
        # Since we use sets, we don't know the order in which validators
        # will be applied.
        # we've set both validators to fail, and we'll check that only one
        # of them was called
        self.req_body_dict["request"]["object"]["spec"]["features"][
            "services"
        ] = ["ok", "fail"]
        req_body = json.dumps(self.req_body_dict)
        req = mock.MagicMock(stream=io.StringIO(req_body))
        self.controller.on_post(req, self.resp)
        self.assertIn("400", self.resp.body)
        self.assertIn("VIKINGS!", self.resp.body)
        # check that only one validator was called
        self.assertEqual(1, ok_mock.call_count + fail_mock.call_count)


class TestOpenStackValidator(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.validate = osv.OpenStackValidator().validate
        self.req = {"operation": "UPDATE", "object": {}, "oldObject": {}}

    def test_upgrade(self):
        self.req["object"] = {"spec": {"openstack_version": "train"}}
        self.req["oldObject"] = {"spec": {"openstack_version": "stein"}}
        self.assertIsNone(self.validate(self.req))

    def test_downgrade(self):
        self.req["object"] = {"spec": {"openstack_version": "stein"}}
        self.req["oldObject"] = {"spec": {"openstack_version": "train"}}
        with self.assertRaises(exception.OsDplValidationFailed):
            self.validate(self.req)

    def test_skiplevel_upgrade(self):
        self.req["object"] = {"spec": {"openstack_version": "train"}}
        self.req["oldObject"] = {"spec": {"openstack_version": "rocky"}}
        with self.assertRaises(exception.OsDplValidationFailed):
            self.validate(self.req)

    def upgrade_to_master(self):
        self.req["object"] = {"spec": {"openstack_version": "master"}}
        self.req["oldObject"] = {"spec": {"openstack_version": "train"}}
        self.assertIsNone(self.validate(self.req))

    def upgrade_with_extra_changes(self):
        self.req["object"] = {"spec": {"openstack_version": "train"}}
        self.req["oldObject"] = {
            "spec": {"openstack_version": "stein", "spam": "ham"}
        }
        with self.assertRaises(exception.OsDplValidationFailed):
            self.validate(self.req)

    def test_openstackversion_latest(self):
        self.assertEqual(
            osv.OpenStackVersion.latest,
            osv.OpenStackVersion.train,
            "Latest version is not Train",
        )

    def test_openstackversion_master(self):
        for v in osv.OpenStackVersion:
            if v != osv.OpenStackVersion.master:
                self.assertLess(
                    v,
                    osv.OpenStackVersion.master,
                    "openstack/master is not the largest possible version",
                )


class TestNeutronValidator(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.validate = neutron.NeutronValidator().validate
        self.req = {"object": {"spec": {"features": {"neutron": {}}}}}

    def test_physnet_required_no_tf(self):
        with self.assertRaises(exception.OsDplValidationFailed):
            self.validate(self.req)

    def test_tf_physnet_optional(self):
        self.req["object"]["spec"]["features"]["neutron"] = {
            "backend": "tungstenfabric"
        }
        self.assertIsNone(self.validate(self.req))
