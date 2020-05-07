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


class NeutronValidator(base.BaseValidator):
    service = "networking"

    def validate(self, review_request):
        neutron_features = (
            review_request.get("object", {})
            .get("spec", {})
            .get("features", {})
            .get("neutron", {})
        )
        neutron_backend = neutron_features.get("backend")
        floating_network = neutron_features.get("floating_network", {})
        if neutron_backend != "tungstenfabric" and not floating_network.get(
            "physnet"
        ):
            raise exception.OsDplValidationFailed(
                "Malformed OpenStackDeployment spec, if TungstenFabric is "
                "not used, physnet needs to be specified in "
                "features.neutron.floating_network section."
            )
