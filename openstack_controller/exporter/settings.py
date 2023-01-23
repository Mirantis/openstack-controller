#    Copyright 2023 Mirantis, Inc.
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

OSCTL_EXPORTER_CERTIFICATES_INFO_FILE = os.getenv(
    "OSCTL_EXPORTER_CERTIFICATES_INFO_FILE",
    "/etc/openstack-controller/certs_info.yaml",
)

# Port to start exporter
OSCTL_EXPORTER_BIND_PORT = int(os.getenv("OSCTL_EXPORTER_BIND_PORT", 9102))

# List of enabled collectors
OSCTL_EXPORTER_ENABLED_COLLECTORS = os.getenv(
    "OSCTL_EXPORTER_ENABLED_COLLECTORS",
    "osdpl_certificate,osdpl_nova,osdpl_ironic",
).split(",")

# Number in seconds we allow for polling, when exceeds exporter is stopped.
OSCTL_EXPORTER_MAX_POLL_TIMEOUT = int(
    os.getenv("OSCTL_EXPORTER_MAX_POLL_TIMEOUT", "300")
)
