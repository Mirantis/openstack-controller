import datetime

import kopf

from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import utils

LOG = utils.get_logger(__name__)


@kopf.on.field("", "v1", "nodes", field="status.conditions")
async def node_status_update_handler(name, body, old, new, event, **kwargs):
    LOG.debug(f"Handling node status {event} event.")
    LOG.debug(f"The new state is {new}")

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
        f"The node: {name} is not ready for {not_ready_for.seconds}s. Removing pods..."
    )
    node.remove_pods(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)
