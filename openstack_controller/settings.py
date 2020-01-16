#    Copyright 2020 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import os

# The number of seconds to wait for all component from application becomes ready
OSCTL_WAIT_APPLICATION_READY_TIMEOUT = os.environ.get(
    "OSCTL_WAIT_APPLICATION_READY_TIMEOUT", 600
)

# The number of seconds to sleep between checking application ready attempts
OSCTL_WAIT_APPLICATION_READY_DELAY = os.environ.get(
    "OSCTL_WAIT_APPLICATION_READY_DELAY", 10
)

# The number of seconds to wait for values set in manifest are propagated to child objects.
OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT = os.environ.get(
    "OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT", 300
)

# The number of seconds between attempts to check that values were applied.
OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY = os.environ.get(
    "OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY", 10
)

# The number of seconds to wait for values are removed from manifest and propagated to child objects.
OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT = os.environ.get(
    "OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT", 300
)

# The number of seconds between attempts to check that values were removed from release.
OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY = os.environ.get(
    "OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY", 10
)

# The number of seconds to wait for kubernetes object removal
OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT = os.environ.get(
    "OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT", 300
)

# The number of seconds between attempts to check that kubernetes object is removed
OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY = os.environ.get(
    "OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY", 300
)

# The number of seconds to pause for helmbundle changes
OSCTL_HELMBUNDLE_APPLY_DELAY = os.environ.get(
    "OSCTL_HELMBUNDLE_APPLY_DELAY", 10
)
