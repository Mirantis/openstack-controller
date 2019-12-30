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


class KeystoneValidator(base.BaseValidator):
    service = "identity"

    def validate(self, review_request, response):
        keycloak_section = (
            review_request.get("object", {})
            .get("spec", {})
            .get("features", {})
            .get("keystone", {})
            .get("keycloak", {})
        )
        if (
            keycloak_section.get("enabled", False)
            and keycloak_section.get("oidc", {}).get("OIDCSSLValidateServer")
            is None
        ):
            response.set_error(
                400,
                (
                    "Malformed OpenStackDeployment spec, if keycloak is "
                    "enabled for identity service, you need to specify if "
                    "you want to enable OIDC SSL validation."
                ),
            )
