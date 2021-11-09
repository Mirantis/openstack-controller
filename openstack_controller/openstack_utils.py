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

import asyncio
import base64
from datetime import datetime

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


def get_keystone_admin_creds():

    global ADMIN_CREDS
    if ADMIN_CREDS:
        return ADMIN_CREDS

    keystone_secret = kube.resource_list(
        pykube.Secret,
        None,
        settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
    ).get_or_none(name=constants.COMPUTE_NODE_CONTROLLER_SECRET_NAME)

    if keystone_secret is None:
        raise kopf.TemporaryError(
            "Keystone admin secret not found, can not get keystone admin creds."
        )
    ADMIN_CREDS = {}
    for k, v in keystone_secret.obj["data"].items():
        ADMIN_CREDS[
            (k[3:] if k.startswith("OS_") else k).lower()
        ] = base64.b64decode(v).decode("utf-8")

    return ADMIN_CREDS


async def find_nova_cell_setup_cron_job(node_uid):
    def get_nova_cell_setup_job():
        return kube.resource_list(
            pykube.CronJob, None, settings.OSCTL_OS_DEPLOYMENT_NAMESPACE
        ).get_or_none(name="nova-cell-setup")

    try:
        cronjob = await asyncio.wait_for(
            utils.async_retry(get_nova_cell_setup_job), timeout=300
        )
    except asyncio.TimeoutError:
        raise kopf.TemporaryError(
            "nova-cell-setup cron job not found, can not discover the "
            "newly added compute host"
        )
    job = {
        "metadata": {
            "name": f"nova-cell-setup-online-{node_uid}",
            "namespace": settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
            "annotations": cronjob.obj["metadata"]["annotations"],
            "labels": cronjob.obj["spec"]["jobTemplate"]["metadata"]["labels"],
        },
        "spec": cronjob.obj["spec"]["jobTemplate"]["spec"],
    }
    job["spec"]["backoffLimit"] = 10
    job["spec"]["ttlSecondsAfterFinished"] = 60
    job["spec"]["template"]["spec"]["restartPolicy"] = "OnFailure"
    return job


class OpenStackClientManager:
    def __init__(self, creds=None):
        if not creds:
            creds = get_keystone_admin_creds()
        self.oc = openstack.connect(**creds)

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
