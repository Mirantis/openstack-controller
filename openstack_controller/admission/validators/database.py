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

from openstack_controller.admission.validators import base
from openstack_controller import exception


class DatabaseValidator(base.BaseValidator):
    service = "database"

    def validate(self, review_request):
        db_section = (
            review_request.get("object", {})
            .get("spec", {})
            .get("features", {})
            .get("database", {})
        )
        self._check_backup_backend(db_section)

    def _check_backup_backend(self, db_section):
        backup_section = db_section.get("backup", {})
        if backup_section.get(
            "backend", "pvc"
        ) == "pv_nfs" and not backup_section.get("pv_nfs", {}):
            raise exception.OsDplValidationFailed(
                "When backup backend is set to pv_nfs, pv_nfs.server and pv_nfs.path options are required"
            )
