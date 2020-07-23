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

from openstack_controller.admission.validators import base
from openstack_controller import constants
from openstack_controller import exception


class OpenStackValidator(base.BaseValidator):
    """Validates general sanity of OpenStackDeployment"""

    service = "openstack"

    def validate(self, review_request):
        old_obj = review_request.get("oldObject", {})
        new_obj = review_request.get("object", {})
        self._deny_master(new_obj)
        if review_request["operation"] == "UPDATE":
            # on update we deffinitely have both old and new as not empty
            self._validate_openstack_upgrade(old_obj, new_obj)

    def _deny_master(self, new_obj):
        new_version = new_obj.get("spec", {}).get("openstack_version")
        if new_version == "master":
            raise exception.OsDplValidationFailed(
                "Using master of OpenStack is not permitted. "
                "You must disable the OpenStackDeployment admission "
                "controller to deploy, use or upgrade to master."
            )

    def _validate_openstack_upgrade(self, old_obj, new_obj):
        # NOTE(pas-ha) this logic relies on 'master' already has been denied
        old_version = constants.OpenStackVersion[
            old_obj["spec"]["openstack_version"]
        ]
        new_version = constants.OpenStackVersion[
            new_obj["spec"]["openstack_version"]
        ]
        # not an upgrade
        if new_version == old_version:
            return
        if old_version > new_version:
            raise exception.OsDplValidationFailed(
                "OpenStack version downgrade is not permitted"
            )
        if new_version.value - old_version.value != 1:
            raise exception.OsDplValidationFailed(
                "Skip-level OpenStack version upgrade is not permitted"
            )
        # validate that nothing else is changed together with
        # openstack_version
        _old_spec = copy.deepcopy(old_obj["spec"])
        _old_spec.pop("openstack_version")
        _new_spec = copy.deepcopy(new_obj["spec"])
        _new_spec.pop("openstack_version")
        if _new_spec != _old_spec:
            raise exception.OsDplValidationFailed(
                "If spec.openstack_version is changed, "
                "changing other values in the spec is not permitted."
            )
