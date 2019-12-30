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


class BarbicanValidator(base.BaseValidator):
    service = "key-manager"

    def validate(self, review_request, response):
        features = (
            review_request.get("object", {})
            .get("spec", {})
            .get("features", {})
        )
        if "backend" not in features.get("barbican", {}):
            response.set_error(
                400,
                (
                    "Malformed OpenStackDeployment spec, if key-manager "
                    "is enabled, you need to specify the desired backend."
                ),
            )
