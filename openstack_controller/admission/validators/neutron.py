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

    def _check_bgpvpn(self, bgpvpn):
        if not bgpvpn.get("route_reflector", {}).get("enabled"):
            if not bgpvpn.get("peers"):
                raise exception.OsDplValidationFailed(
                    "Either neutron:bgpvpn:peers or "
                    "neutron:bgpvpn:route_reflector have to be specified"
                )

    def validate(self, review_request):
        spec = review_request.get("object", {}).get("spec", {})
        neutron_features = spec.get("features", {}).get("neutron", {})
        floating_network = neutron_features.get("floating_network", {})
        ipsec = neutron_features.get("ipsec", {"enabled": False})
        bgpvpn = neutron_features.get("bgpvpn", {"enabled": False})
        tungstenfabric_enabled = spec["preset"] == "compute-tf"

        if not tungstenfabric_enabled:
            if floating_network.get("enabled") and not floating_network.get(
                "physnet"
            ):
                raise exception.OsDplValidationFailed(
                    "Malformed OpenStackDeployment spec, if TungstenFabric is "
                    "not used, physnet needs to be specified in "
                    "features.neutron.floating_network section."
                )
            if bgpvpn["enabled"]:
                self._check_bgpvpn(bgpvpn)
        else:
            if ipsec["enabled"]:
                raise exception.OsDplValidationFailed(
                    "TungstenFabric with IPsec is not supported"
                )
            if bgpvpn["enabled"]:
                raise exception.OsDplValidationFailed(
                    "TungstenFabric with BGPVPN is not supported"
                )
            if floating_network.get("enabled"):
                network_options = [
                    floating_network.get(k)
                    for k in ["network_type", "physnet", "segmentation_id"]
                ]
                if any(network_options) and not all(network_options):
                    raise exception.OsDplValidationFailed(
                        "TungstenFabric as network backend and setting of "
                        "floating network physnet name without network type "
                        "and segmentation id are not compatible."
                    )
