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

import datetime

import kopf

from openstack_controller import constants as const
from openstack_controller import kube
from openstack_controller import maintenance
from openstack_controller import openstack_utils as ostutils
from openstack_controller import settings
from openstack_controller import utils

LOG = utils.get_logger(__name__)


@kopf.on.field("", "v1", "nodes", field="status.conditions")
async def node_status_update_handler(name, body, old, new, reason, **kwargs):
    LOG.debug(f"Handling node status {reason} event.")
    LOG.info(f"The node {name} changes are: {kwargs['diff']}")

    osdpl = kube.get_osdpl()
    if not osdpl or not osdpl.exists():
        LOG.info("Can't find OpenStackDeployment object")
        return

    # NOTE(vsaienko) get conditions from the object to avoid fake reporing by
    # calico when kubelet is down on the node.
    # Do not remove pods from flapping node.
    node = kube.Node(kube.api, body)
    if node.ready:
        return True

    not_ready_delta = datetime.timedelta(
        seconds=settings.OSCTL_NODE_NOT_READY_FLAPPING_TIMEOUT
    )

    now = last_transition_time = datetime.datetime.utcnow()

    for cond in node.obj["status"]["conditions"]:
        if cond["type"] == "Ready":
            last_transition_time = datetime.datetime.strptime(
                cond["lastTransitionTime"], "%Y-%m-%dT%H:%M:%SZ"
            )
    not_ready_for = now - last_transition_time
    if now - not_ready_delta < last_transition_time:
        raise kopf.TemporaryError(
            f"The node is not ready for {not_ready_for.seconds}s",
        )
    LOG.info(f"The node {name} is not ready for {not_ready_for.seconds}s.")

    # NOTE(pas-ha): guard against node being in maintenance
    # when node is already being drained
    # we assume that at this stage the workflow with NodeWorkloadLocks
    # and auto-migration of workloads is happening instead of using Masakari
    if node.has_role(const.NodeRole.compute):
        # NOTE(vsaienko): when maintenance is over and node added back to scheduling
        # there is time frame when nova-compute is still startin. Do not notify
        # Masakary when node is under maintenance.
        nwl = maintenance.NodeWorkloadLock.get_resource(name)
        if not node.unschedulable or nwl.is_maintenance():
            LOG.info(
                f"Notifying HA service on OpenStack compute host {name} down."
            )
        await ostutils.notify_masakari_host_down(node)

    LOG.info(f"Removing pods from node {name}")
    node.remove_pods(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)


# NOTE(avolkov): watching for update events covers
# the case when node is relabeled and NodeWorkloadLock
# has to be created/deleted accordingly
@kopf.on.create("", "v1", "nodes")
@kopf.on.update("", "v1", "nodes")
@kopf.on.resume("", "v1", "nodes")
async def node_change_handler(body, reason, **kwargs):
    name = body["metadata"]["name"]
    LOG.info(f"Got event {reason} for node {name}")
    LOG.info(f"The node {name} changes are: {kwargs['diff']}")
    if not settings.OSCTL_NODE_MAINTENANCE_ENABLED:
        LOG.warning("The maintenance API is not enabled.")
        return
    node = kube.Node(kube.api, body)
    nwl = maintenance.NodeWorkloadLock.get_resource(name)
    if nwl.required_for_node(node):
        nwl.present()
    else:
        LOG.info(
            f"We do not have OS workloads on node {name} anymore. Remove NodeWorkloadLock."
        )
        nwl.absent()


@kopf.on.delete("", "v1", "nodes")
async def node_delete_handler(body, **kwargs):
    name = body["metadata"]["name"]
    LOG.info(f"Got delete event for node {name}")
    nwl = maintenance.NodeWorkloadLock.get_resource(name)
    nwl.absent()
