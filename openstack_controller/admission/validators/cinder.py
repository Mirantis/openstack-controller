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

from openstack_controller import constants
from openstack_controller.admission.validators import base
from openstack_controller import exception


class CinderValidator(base.BaseValidator):
    service = "block-storage"

    def validate(self, review_request):
        spec = review_request.get("object", {}).get("spec", {})
        cinder_section = spec.get("features", {}).get("cinder", {})

        self._check_custom_backup_driver_allowed(spec)
        self._check_backup_drivers_count(cinder_section)

    def _check_custom_backup_driver_allowed(self, spec):
        openstack_version = spec["openstack_version"]
        drivers_section = (
            spec.get("features", {})
            .get("cinder", {})
            .get("backup", {})
            .get("drivers", {})
        )

        if drivers_section:
            if (
                constants.OpenStackVersion[openstack_version].value
                < constants.OpenStackVersion["yoga"].value
            ):
                raise exception.OsDplValidationFailed(
                    "Custom Cinder backup driver is allowed from Yoga release."
                )

    def _check_backup_drivers_count(self, cinder_section):
        backup_section = cinder_section.get("backup", {})
        if not backup_section:
            return
        if backup_section.get("enabled", True):
            backup_drivers = backup_section.get("drivers", {})
            enabled_drivers = [
                name for name, vol in backup_drivers.items() if vol["enabled"]
            ]
            if len(enabled_drivers) > 1:
                raise exception.OsDplValidationFailed(
                    "Must be enabled one Cinder backup driver"
                )
