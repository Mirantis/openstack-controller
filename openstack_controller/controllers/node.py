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

from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import utils

LOG = utils.get_logger(__name__)


@kopf.on.field("", "v1", "nodes", field="status.conditions")
@utils.collect_handler_metrics
async def node_status_update_handler(name, body, old, new, event, **kwargs):
    LOG.debug(f"Handling node status {event} event.")
    LOG.info(f"The node {name} changes are: {kwargs['diff']}")

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
    LOG.info(
        f"The node: {name} is not ready for {not_ready_for.seconds}s. "
        f"Removing pods..."
    )
    node.remove_pods(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)


# NOTE(avolkov): watching for update events covers
# the case when node is relabeled and NodeWorkloadLock
# has to be created/deleted accordingly
@kopf.on.create("", "v1", "nodes")
@kopf.on.update("", "v1", "nodes")
@kopf.on.resume("", "v1", "nodes")
async def node_change_handler(body, event, **kwargs):
    name = body["metadata"]["name"]
    LOG.info(f"Got event {event} for node {name}")
    LOG.info(f"The node {name} changes are: {kwargs['diff']}")
    if not kube.NodeWorkloadLock.definition_exists():
        LOG.warning("No custom resource definition")
        return
    if kube.NodeWorkloadLock.required_for_node(body):
        kube.NodeWorkloadLock.ensure(name)
    else:
        nwl = kube.NodeWorkloadLock.get(name)
        if nwl:
            await nwl.purge()


@kopf.on.delete("", "v1", "nodes")
async def node_delete_handler(body, **kwargs):
    name = body["metadata"]["name"]
    LOG.info(f"Got delete event for node {name}")
    nwl = kube.NodeWorkloadLock.get(name)
    if nwl:
        await nwl.purge()
