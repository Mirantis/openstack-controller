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
import re

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


COMPUTE_SERVICE_DISABLE_REASON = "OSDPL: Node is under maintenance"
VOLUME_SERVICE_DISABLED_REASON = COMPUTE_SERVICE_DISABLE_REASON


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
    def __init__(self, cloud=settings.OS_CLOUD, metrics=None):
        init_keystone_admin_creds()
        # NOTE(vsaienko): disable built in opestacksdk metrics as they
        # leads to deadlock in custom collectors.
        # https://github.com/prometheus/client_python/issues/353
        if metrics is None:
            metrics = {"prometheus": {"enabled": False}}
        self.oc = openstack.connect(cloud=cloud, metrics=metrics)

    def volume_get_services(self, **kwargs):
        res = []
        params = {k: v for k, v in kwargs.items() if v is not None}
        resp = self.oc.block_storage.get("/os-services", params=params)
        if resp.ok:
            res = resp.json()["services"]
        return res

    def volume_get_volumes(self, host=None, all_tenants=True):
        def match_host(volume, host=None):
            if host is None:
                return True
            volume_host = volume.get("host", "")
            return host == volume_host.split("@")[0]

        return [
            x
            for x in self.oc.block_storage.volumes(all_tenants=all_tenants)
            if match_host(x, host)
        ]

    def volume_ensure_service_disabled(
        self, host, binary="cinder-volume", disabled_reason=None
    ):
        data = {"binary": binary, "host": host}
        if disabled_reason is not None:
            data["disabled_reason"] = disabled_reason
        self.oc.block_storage.put("/os-services/disable-log-reason", json=data)

    def volume_ensure_service_enabled(self, host, binary="cinder-volume"):
        data = {"binary": binary, "host": host}
        self.oc.block_storage.put("/os-services/enable", json=data)

    def compute_get_services(self, host=None, binary="nova-compute"):
        return list(self.oc.compute.services(host=host, binary=binary))

    def compute_ensure_service_enabled(self, service):
        if service["status"].lower() != "enabled":
            self.oc.compute.update_service(service["id"], status="enabled")

    def compute_ensure_service_disabled(self, service, disabled_reason=None):
        if service["status"].lower() != "disabled":
            self.oc.compute.update_service(
                service["id"],
                status="disabled",
                disabled_reason=disabled_reason,
            )

    def compute_ensure_services_absent(self, host):
        for service in self.compute_get_services(host=host, binary=None):
            self.oc.compute.delete_service(service)

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

    def compute_get_availability_zones(self, details=False):
        return list(self.oc.compute.availability_zones(details=details))

    def baremetal_get_nodes(self):
        return self.oc.baremetal.nodes()

    def baremetal_is_node_available(self, node):
        """Check if node is available for provisioning

        The node is threated as available for provisioning when:
        1. maintenance flag is Flase
        2. No instance_uuid is assigned
        3. The provision_state is available

        """

        return all(
            # TODO(vsaienko) use maintenance, instance_uuid
            # when switch to osclient of zed version.
            [
                node["is_maintenance"] is False,
                node["instance_id"] is None,
                node["provision_state"] == "available",
            ]
        )

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

    def network_ensure_agents_absent(self, host):
        for agent in self.network_get_agents(host=host):
            self.oc.network.delete_agent(agent)


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
        # NOTE(vsaienko): do not resend notifications if host does not belong
        # to any segments.
        if re.search("Host with name .* could not be found.", str(e)):
            LOG.warning(e)
            return
        LOG.warning(f"Failed to notify Masakari - {e}")
        raise kopf.TemporaryError(f"{e}") from e
