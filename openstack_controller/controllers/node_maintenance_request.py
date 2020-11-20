import kopf
import pykube

from openstack_controller import kube
from openstack_controller.services import base
from openstack_controller import settings
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


async def _run_service_methods(services, methods, node_metadata):
    for service, service_class in services:
        for method_name in methods:
            await getattr(service_class, method_name)(node_metadata)


if settings.OSCTL_ENABLE_NODE_MAINTENANCE_REQUEST_PROCESSING:

    @kopf.on.create(*kube.NodeMaintenanceRequest.kopf_on_args)
    @kopf.on.update(*kube.NodeMaintenanceRequest.kopf_on_args)
    @kopf.on.resume(*kube.NodeMaintenanceRequest.kopf_on_args)
    async def node_maintenance_request_change_handler(body, **kwargs):
        name = body["metadata"]["name"]
        node_name = body["spec"]["nodeName"]
        LOG.info(f"Got node maintenance request change event {name}")
        node = kube.find(pykube.Node, node_name)
        if not kube.NodeWorkloadLock.required_for_node(node.obj):
            return

        nwl = kube.NodeWorkloadLock.ensure(node_name)

        if nwl.is_active():
            LOG.info(f"Preparing for maintenance for node {name}")
            nwl.set_state("prepare_inactive")
            try:
                await _run_service_methods(
                    ORDERED_SERVICES,
                    ["prepare_node_after_reboot", "add_node_to_scheduling"],
                    node.obj["metadata"],
                )
            except Exception:
                nwl.set_state("failed")
                LOG.exception(
                    f"Failed to get node {name} to maintenance state"
                )
                # NOTE(avolkov): in case of errors with resource evacuation
                # NodeWorkloadLock moves to a failed state and operator
                # should manually resolve the issues and set lock back to an active state
                raise kopf.PermanentError(
                    "Operator attention is required to continue maintenance"
                )
            nwl.set_state("inactive")
            LOG.info(f"Maintenance started for node {name}")

    @kopf.on.delete(*kube.NodeMaintenanceRequest.kopf_on_args)
    async def node_maintenance_request_delete_handler(body, **kwargs):
        name = body["metadata"]["name"]
        node_name = body["spec"]["nodeName"]
        LOG.info(f"Got node maintenance request delete event {name}")
        node = kube.find(pykube.Node, node_name)
        if not kube.NodeWorkloadLock.required_for_node(node.obj):
            return

        nwl = kube.NodeWorkloadLock.ensure(node_name)

        if nwl.is_maintenance():
            LOG.info(f"Preparing to stop maintenance for node {name}")
            nwl.set_state("prepare_active")
            try:
                await _run_service_methods(
                    list(reversed(ORDERED_SERVICES)),
                    ["remove_node_from_scheduling", "prepare_for_node_reboot"],
                    node.obj["metadata"],
                )
            except Exception:
                nwl.set_state("failed")
                LOG.exception(f"Failed to get node {name} to active state")
                raise
            nwl.set_state("active")
            LOG.info(f"Maintenance stopped for node {name}")
