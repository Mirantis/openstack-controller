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
    def validate(self, review_request, response):
        pass


class FailValidator(base.BaseValidator):
    def validate(self, review_request, response):
        response.set_error(400, "Foo")


FAKE_VALIDATORS = {"ok": OkValidator(), "fail": FailValidator()}


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
        FAKE_VALIDATORS["ok"], "validate", wraps=FAKE_VALIDATORS["ok"].validate
    )
    @mock.patch.object(
        FAKE_VALIDATORS["fail"],
        "validate",
        wraps=FAKE_VALIDATORS["fail"].validate,
    )
    @mock.patch.object(controller, "_VALIDATORS", FAKE_VALIDATORS)
    def test_validate_validators_order_both_called(self, fail_mock, ok_mock):
        self.req_body_dict["request"]["object"]["spec"]["features"][
            "services"
        ] = ["ok", "fail"]
        req_body = json.dumps(self.req_body_dict)
        req = mock.MagicMock(stream=io.StringIO(req_body))
        self.controller.on_post(req, self.resp)
        ok_mock.assert_called_once()
        fail_mock.assert_called_once()
        self.assertIn("400", self.resp.body)
        self.assertIn("Foo", self.resp.body)

    @mock.patch.object(
        FAKE_VALIDATORS["ok"], "validate", wraps=FAKE_VALIDATORS["ok"].validate
    )
    @mock.patch.object(
        FAKE_VALIDATORS["fail"],
        "validate",
        wraps=FAKE_VALIDATORS["fail"].validate,
    )
    @mock.patch.object(controller, "_VALIDATORS", FAKE_VALIDATORS)
    def test_validate_validators_stop_after_first_fail(
        self, fail_mock, ok_mock
    ):
        self.req_body_dict["request"]["object"]["spec"]["features"][
            "services"
        ] = ["fail", "ok"]
        req_body = json.dumps(self.req_body_dict)
        req = mock.MagicMock(stream=io.StringIO(req_body))
        self.controller.on_post(req, self.resp)
        ok_mock.assert_not_called()
        fail_mock.assert_called_once()
        self.assertIn("400", self.resp.body)
        self.assertIn("Foo", self.resp.body)
