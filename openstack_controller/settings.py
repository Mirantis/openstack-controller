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

import kopf

# The number of seconds to wait for all component from application becomes ready
OSCTL_WAIT_APPLICATION_READY_TIMEOUT = int(
    os.environ.get("OSCTL_WAIT_APPLICATION_READY_TIMEOUT", 1200)
)

# The number of seconds to sleep between checking application ready attempts
OSCTL_WAIT_APPLICATION_READY_DELAY = int(
    os.environ.get("OSCTL_WAIT_APPLICATION_READY_DELAY", 10)
)

# The number of seconds to wait for values set in manifest are propagated to child objects.
OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT", 600)
)

# The number of seconds between attempts to check that values were applied.
OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY", 10)
)

# The number of seconds to wait for values are removed from manifest and propagated to child objects.
OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT", 600)
)

# The number of seconds between attempts to check that values were removed from release.
OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY", 10)
)

# The number of seconds to wait for kubernetes object removal
OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT", 600)
)

# The number of seconds between attempts to check that kubernetes object is removed
OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY", 10)
)

# The number of seconds to pause for helmbundle changes
OSCTL_HELMBUNDLE_APPLY_DELAY = int(
    os.environ.get("OSCTL_HELMBUNDLE_APPLY_DELAY", 10)
)

# The amount of time to wit for flapping node
OSCTL_NODE_NOT_READY_FLAPPING_TIMEOUT = int(
    os.environ.get("OSCTL_NODE_NOT_READY_FLAPPING_TIMEOUT", 120)
)

# The name of openstack deployment namespace
OSCTL_OS_DEPLOYMENT_NAMESPACE = os.environ.get(
    "OSCTL_OS_DEPLOYMENT_NAMESPACE", "openstack"
)

# The number of retries while waiting a resouce deleted
OSCTL_RESOURCE_DELETED_WAIT_RETRIES = int(
    os.environ.get("OSCTL_RESOURCE_DELETED_WAIT_RETRIES", 120)
)

# The number of seconds to sleep while waiting a resouce deleted
OSCTL_RESOURCE_DELETED_WAIT_TIMEOUT = int(
    os.environ.get("OSCTL_RESOURCE_DELETED_WAIT_TIMEOUT", 1)
)

OSCTL_REDIS_NAMESPACE = os.environ.get(
    "OSCTL_REDIS_NAMESPACE", "openstack-redis"
)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.watching.connect_timeout = 1 * 60
    settings.watching.server_timeout = os.environ.get(
        "KOPF_WATCH_STREAM_TIMEOUT", 1 * 60
    )
    settings.watching.client_timeout = 1 * 60

    settings.session.total_timeout = 1 * 60
    settings.session.sock_connect_timeout = 1 * 30
    settings.session.sock_read_timeout = 1 * 10
    settings.session.connect = 1 * 30
