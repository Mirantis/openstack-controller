import kopf
import pykube

from openstack_controller import kube
from openstack_controller.services import base
from openstack_controller import utils

LOG = utils.get_logger(__name__)

# Higher value means that component's prepare-usage handlers will be called
# later and prepare-shutdown handlers - sooner
SERVICE_ORDER = {"compute": 100}
ORDERED_SERVICES = list(
    sorted(
        filter(
            lambda tup: tup[0] in SERVICE_ORDER,
            base.Service.registry.items(),
        ),
        key=lambda tup: SERVICE_ORDER[tup[0]],
    )
)

MAINTENANCE = "maintenance"
OPERATIONAL = "operational"


async def _run_service_methods(services, methods, node_metadata):
    for service, service_class in services:
        for method_name in methods:
            await getattr(service_class, method_name)(node_metadata)


async def _make_state_transition(operation, nwl, node, retry):
    name = node.obj["metadata"]["name"]
    if operation == MAINTENANCE:
        args = [
            ORDERED_SERVICES,
            ["remove_node_from_scheduling", "prepare_for_node_reboot"],
            node.obj["metadata"],
        ]
        states = {
            "prepare": "prepare_inactive",
            "temporary_failure": "active",
            "final": "inactive",
        }
    elif operation == OPERATIONAL:
        args = [
            list(reversed(ORDERED_SERVICES)),
            ["prepare_node_after_reboot", "add_node_to_scheduling"],
            node.obj["metadata"],
        ]
        states = {
            "prepare": "prepare_active",
            "temporary_failure": "inactive",
            "final": "active",
        }
    else:
        raise kopf.PermanentError("Got unknown operation")

    LOG.info(f"Preparing node {name} for {operation} state")
    nwl.set_state(states["prepare"])
    try:
        await _run_service_methods(*args)
    except Exception:
        nwl.set_state(states["temporary_failure"])
        LOG.exception(
            f"Failed to get node {name} to {operation} state, attempt number {retry}"
        )
        raise kopf.TemporaryError(
            "Maintenance request processing temporarily failed"
        )
    nwl.set_state(states["final"])
    LOG.info(f"{operation} state is applied for node {name}")


@kopf.on.create(*kube.NodeMaintenanceRequest.kopf_on_args)
@kopf.on.update(*kube.NodeMaintenanceRequest.kopf_on_args)
@kopf.on.resume(*kube.NodeMaintenanceRequest.kopf_on_args)
async def node_maintenance_request_change_handler(body, retry, **kwargs):
    name = body["metadata"]["name"]
    node_name = body["spec"]["nodeName"]
    LOG.info(f"Got node maintenance request change event {name}")
    node = kube.find(pykube.Node, node_name)
    if not kube.NodeWorkloadLock.required_for_node(node.obj):
        return

    nwl = kube.NodeWorkloadLock.ensure(node_name)

    if nwl.is_active():
        await _make_state_transition(MAINTENANCE, nwl, node, retry)


@kopf.on.delete(*kube.NodeMaintenanceRequest.kopf_on_args)
async def node_maintenance_request_delete_handler(body, retry, **kwargs):
    name = body["metadata"]["name"]
    node_name = body["spec"]["nodeName"]
    LOG.info(f"Got node maintenance request delete event {name}")
    node = kube.find(pykube.Node, node_name)
    if not kube.NodeWorkloadLock.required_for_node(node.obj):
        return

    nwl = kube.NodeWorkloadLock.ensure(node_name)

    if nwl.is_maintenance():
        await _make_state_transition(OPERATIONAL, nwl, node, retry)
