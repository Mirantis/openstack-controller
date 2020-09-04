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

import kopf
import openstack
import openstack.exceptions
import pykube

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import utils

LOG = utils.get_logger(__name__)


async def get_keystone_admin_creds():
    def get_keystone_admin_secret():
        return kube.resource_list(
            pykube.Secret,
            None,
            settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
        ).get_or_none(name=constants.COMPUTE_NODE_CONTROLLER_SECRET_NAME)

    try:
        keystone_secret = await asyncio.wait_for(
            utils.async_retry(get_keystone_admin_secret),
            timeout=300,
        )
    except asyncio.TimeoutError:
        raise kopf.TemporaryError(
            "keystone admin secret not found, can not discover the newly "
            "added compute host"
        )
    creds = {}
    for k, v in keystone_secret.obj["data"].items():
        creds[
            (k[3:] if k.startswith("OS_") else k).lower()
        ] = base64.b64decode(v).decode("utf-8")
    return creds


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


async def get_openstack_connection():
    creds = await get_keystone_admin_creds()
    return openstack.connect(**creds)


def get_single_service(os_connection, host=None, binary="nova-compute"):
    response = os_connection.compute.get(
        f"/os-services?host={host}&binary={binary}"
    )
    openstack.exceptions.raise_from_response(response)
    services = response.json()["services"]
    if len(services) == 1:
        return services[0]


async def migrate_servers(
    *,
    openstack_connection,
    migrate_func,
    servers,
    migrating_off,
    concurrency=None,
):
    if concurrency is None:
        concurrency = len(servers)
    groups = utils.divide_into_groups_of(concurrency, servers)
    for group in groups:
        for server in group:
            migrate_func(server)
            # TODO(vdrok): if, at this point, the controller gets restarted,
            # but it already started the migration, the retry of the handler
            # will fail as servers already started migrating, and they can not
            # accept another live migrate task anymore. Handle this by looking
            # at the error message, it should contain something like
            # "Cannot 'os-migrateLive' instance ...  while it is in
            # task_state migrating"

        def wait_all_servers_have_migrated():
            current_servers = [
                openstack_connection.compute.get_server(s) for s in group
            ]
            LOG.info(
                f"Migrating servers, they currently are in state: "
                f"{[(s.hostname, s.status) for s in current_servers]}"
            )
            # TODO(vdrok): if any of the servers fall into error state,
            #              stop immediately and don't retry
            return all(
                s.hostname != migrating_off and s.status == "ACTIVE"
                for s in current_servers
            )

        try:
            await asyncio.wait_for(
                utils.async_retry(wait_all_servers_have_migrated),
                timeout=300,
            )
        except asyncio.TimeoutError:
            raise kopf.PermanentError(
                "Can not move instances off of deleted host"
            )
