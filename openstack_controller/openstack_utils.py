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

import base64
from datetime import datetime
from enum import IntEnum
import os

from keystoneauth1 import exceptions as ksa_exceptions
import kopf
import openstack
import pykube

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import utils

LOG = utils.get_logger(__name__)

ADMIN_CREDS = None


class SERVER_POWER_STATES(IntEnum):
    NOSTATE = 0
    RUNNING = 1
    PAUSED = 3
    SHUTDOWN = 4
    CRASHED = 6
    SUSPENDED = 7


# States save to host reboot.
SERVER_STOPPED_POWER_STATES = [
    SERVER_POWER_STATES.SHUTDOWN,
    SERVER_POWER_STATES.CRASHED,
    SERVER_POWER_STATES.SUSPENDED,
]


# NOTE(vsaienko): skip pausing on instances in following states, as they are not running.
# Avoid adding error here, as in this state instance might be running state.
SERVER_STATES_SAFE_FOR_REBOOT = [
    "building",
    "deleted",
    "soft_deleted",
    "stopped",
    "suspended",
    "shelved",
    "shelve_offloaded",
]


def init_keystone_admin_creds():

    if os.path.exists(settings.OS_CLIENT_CONFIG_FILE):
        return

    keystone_secret = kube.resource_list(
        pykube.Secret,
        None,
        settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
    ).get_or_none(name=constants.COMPUTE_NODE_CONTROLLER_SECRET_NAME)

    if keystone_secret is None:
        raise kopf.TemporaryError(
            "Keystone admin secret not found, can not get keystone admin creds."
        )

    clouds_yaml = base64.b64decode(
        keystone_secret.obj["data"]["clouds.yaml"]
    ).decode("utf-8")
    with open(settings.OS_CLIENT_CONFIG_FILE, "w") as f:
        f.write(clouds_yaml)


class OpenStackClientManager:
    def __init__(
        self,
        cloud=settings.OS_CLOUD,
    ):
        init_keystone_admin_creds()
        self.oc = openstack.connect(cloud=cloud)

    def compute_get_services(self, host=None, binary="nova-compute"):
        return list(self.oc.compute.services(host=host, binary=binary))

    def compute_ensure_service_enabled(self, service):
        if service["status"].lower() != "enabled":
            self.oc.compute.enable_service(service)

    def compute_ensure_service_disabled(self, service, disabled_reason=None):
        if service["status"].lower() != "disabled":
            self.oc.compute.disable_service(service, disabled_reason)

    def compute_get_all_servers(self, host=None, status=None):
        filters = {}
        if host:
            filters["host"] = host
        if status:
            filters["status"] = status
        return self.oc.list_servers(
            detailed=False, all_projects=True, filters=filters
        )

    def compute_get_servers_valid_for_live_migration(self, host=None):
        servers = []
        for status in ["ACTIVE", "PAUSED"]:
            servers.extend(
                list(self.compute_get_all_servers(host=host, status=status))
            )
        servers = [s for s in servers if s.task_state != "migrating"]
        return servers

    def compute_get_servers_in_migrating_state(self, host=None):
        return self.compute_get_all_servers(host=host, status="MIGRATING")

    def instance_ha_create_notification(
        self, type, hostname, payload, generated_time=None
    ):
        if not generated_time:
            generated_time = datetime.utcnow().isoformat(timespec="seconds")
        return self.oc.instance_ha.create_notification(
            type=type,
            hostname=hostname,
            generated_time=generated_time,
            payload=payload,
        )

    def network_get_agents(
        self, host=None, is_alive=None, is_admin_state_up=None
    ):
        kwargs = {}
        if host is not None:
            kwargs["host"] = host
        if is_alive is not None:
            kwargs["is_alive"] = is_alive
        if is_admin_state_up is not None:
            kwargs["is_admin_state_up"] = is_admin_state_up
        return list(self.oc.network.agents(**kwargs))


async def notify_masakari_host_down(node):
    try:
        os_client = OpenStackClientManager()
        notification = os_client.instance_ha_create_notification(
            type="COMPUTE_HOST",
            hostname=node.name,
            generated_time=datetime.utcnow().isoformat(timespec="seconds"),
            payload={"event": "STOPPED", "host_status": "NORMAL"},
        )
        LOG.info(f"Sent notification {notification} to Masakari API")
    except ksa_exceptions.EndpointNotFound:
        LOG.info("Instance-HA service is not deployed, ignore notifying")
        return
    except Exception as e:
        LOG.warning(f"Failed to notify Masakari - {e}")
        raise kopf.TemporaryError(f"{e}") from e
