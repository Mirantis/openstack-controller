import kopf

from openstack_controller import kube
from openstack_controller.services import base
from openstack_controller import utils
from openstack_controller import layers
from openstack_controller.batch_health import get_health_statuses


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


def maintenance_node_name(body):
    return body["spec"]["nodeName"].split(".")[0]


async def _run_service_methods(services, methods, node_metadata):
    for service, service_class in services:
        for method_name in methods:
            await getattr(service_class, method_name)(node_metadata)


async def check_services_healthy():
    osdpl = kube.get_osdpl()
    statuses = get_health_statuses(osdpl)
    services = [
        base.Service.registry[i](osdpl.obj, LOG, {})
        for i in layers.services(osdpl.obj["spec"], LOG)[0]
    ]
    if not all(service.healthy(statuses) for service in services):
        LOG.info(
            "Some services are not healthy: %s",
            [i.service for i in services if not i.healthy(statuses)],
        )
        raise kopf.TemporaryError("Services are not healthy")
    return True


async def _make_state_transition(new_state, nwl, node, retry):
    name = node.obj["metadata"]["name"]
    if new_state == MAINTENANCE:
        args = [
            ORDERED_SERVICES,
            ["remove_node_from_scheduling", "prepare_for_node_reboot"],
            node,
        ]
        states = {
            "prepare": "prepare_inactive",
            "final": "inactive",
        }
    elif new_state == OPERATIONAL:
        args = [
            list(reversed(ORDERED_SERVICES)),
            ["prepare_node_after_reboot", "add_node_to_scheduling"],
            node,
        ]
        states = {
            "prepare": "prepare_active",
            "final": "active",
        }
    else:
        raise kopf.PermanentError("Got unknown new_state")

    LOG.info(f"Preparing node {name} for {new_state} state")
    nwl.set_inner_state(states["prepare"])
    try:
        if new_state == OPERATIONAL:
            await check_services_healthy()
        await _run_service_methods(*args)
    except Exception:
        LOG.exception(
            f"Failed to get node {name} to {new_state} state, attempt number {retry}"
        )
        raise kopf.TemporaryError(
            "Maintenance request processing temporarily failed"
        )
    finally:
        nwl.set_inner_state(None)

    nwl.set_state(states["final"])
    LOG.info(f"{new_state} state is applied for node {name}")


@kopf.on.create(*kube.NodeMaintenanceRequest.kopf_on_args)
@kopf.on.update(*kube.NodeMaintenanceRequest.kopf_on_args)
@kopf.on.resume(*kube.NodeMaintenanceRequest.kopf_on_args)
async def node_maintenance_request_change_handler(body, retry, **kwargs):
    name = body["metadata"]["name"]
    node_name = maintenance_node_name(body)
    LOG.info(f"Got node maintenance request change event {name}")
    LOG.info(
        f"The node maintenance request {name} changes are: {kwargs['diff']}"
    )
    node = kube.find(kube.Node, node_name)
    if not kube.NodeWorkloadLock.required_for_node(node):
        return

    nwl = kube.NodeWorkloadLock.ensure(node_name)

    if nwl.is_active():
        await _make_state_transition(MAINTENANCE, nwl, node, retry)


@kopf.on.delete(*kube.NodeMaintenanceRequest.kopf_on_args)
async def node_maintenance_request_delete_handler(body, retry, **kwargs):
    name = body["metadata"]["name"]
    node_name = maintenance_node_name(body)
    LOG.info(f"Got node maintenance request delete event {name}")
    node = kube.find(kube.Node, node_name)
    if not kube.NodeWorkloadLock.required_for_node(node):
        return

    nwl = kube.NodeWorkloadLock.ensure(node_name)

    if nwl.is_maintenance():
        await _make_state_transition(OPERATIONAL, nwl, node, retry)
