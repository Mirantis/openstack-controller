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


class GlanceValidator(base.BaseValidator):
    service = "image"

    def validate(self, review_request):
        spec = review_request.get("object", {}).get("spec", {})
        glance_features = spec.get("features", {}).get("glance", {})
        cinder_backends = glance_features.get("backends", {}).get("cinder", {})
        is_default_seen = False
        for backend_name, opts in cinder_backends.items():
            if ("cinder_volume_type" in opts and "backend_name" in opts) or (
                "cinder_volume_type" not in opts and "backend_name" not in opts
            ):
                raise exception.OsDplValidationFailed(
                    "Either cinder_volume_type or backend_name should be configured for glance backend."
                )
            if "backend_name" in opts:
                if len(opts["backend_name"].split(":")) != 2:
                    raise exception.OsDplValidationFailed(
                        "Glance cinder backend_name should be in the following format "
                        "<cinder backend type>:<cinder volume type>"
                    )

            # Ensure only one backend is configured with default=True
            if is_default_seen is False:
                is_default_seen = opts.get("default", False)
            elif opts.get("default", False):
                raise exception.OsDplValidationFailed(
                    "Malformed OpenStackDeployment spec, only one glance backend"
                    f"might be configured as default."
                )
        if cinder_backends and is_default_seen is False:
            raise exception.OsDplValidationFailed(
                "Glance cinder backend should have at least one default backend."
            )
