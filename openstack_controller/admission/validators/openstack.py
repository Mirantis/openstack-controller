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
import enum
import sys

from openstack_controller.admission.validators import base
from openstack_controller import exception


class OpenStackVersion(enum.IntEnum):
    """Ordered OpenStack version"""

    master = sys.maxsize
    queens = 1
    rocky = 2
    stein = 3
    train = 4
    ussuri = 5
    # TODO(pas-ha) update this when adding new supported OpenStack releases
    latest = 5


class OpenStackValidator(base.BaseValidator):
    """Validates general sanity of OpenStackDeployment"""

    service = "openstack"

    def validate(self, review_request):
        old_obj = review_request.get("oldObject", {})
        new_obj = review_request.get("object", {})
        if review_request["operation"] == "UPDATE":
            # on update we deffinitely have both old and new as not empty
            self._validate_openstack_upgrade(old_obj, new_obj)

    def _validate_openstack_upgrade(self, old_obj, new_obj):
        old_version = OpenStackVersion[old_obj["spec"]["openstack_version"]]
        new_version = OpenStackVersion[new_obj["spec"]["openstack_version"]]
        # not an upgrade
        if new_version == old_version:
            return
        # deny downgrades
        if old_version > new_version:
            raise exception.OsDplValidationFailed(
                "Downgrading OpenStack version is not permitted"
            )
        # deny skip-level upgrades
        # but allow upgrade from latest release to master
        # (as by our Enum it would look like skip-level)
        # TODO(pas-ha) might deny upgrades to master at all
        if (
            not (
                old_version == OpenStackVersion.latest
                and new_version == OpenStackVersion.master
            )
            and new_version.value - old_version.value != 1
        ):
            raise exception.OsDplValidationFailed(
                "Skip-level OpenStack upgrade is not permitted"
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
