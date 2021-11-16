import kopf

from openstack_controller import kube
from openstack_controller.services import base
from openstack_controller import health
from openstack_controller import settings
from openstack_controller import utils
from openstack_controller import maintenance
from openstack_controller import osdplstatus


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


def maintenance_node_name(body):
    return body["spec"]["nodeName"].split(".")[0]


@kopf.on.create(*maintenance.NodeMaintenanceRequest.kopf_on_args)
@kopf.on.update(*maintenance.NodeMaintenanceRequest.kopf_on_args)
@kopf.on.resume(*maintenance.NodeMaintenanceRequest.kopf_on_args)
async def node_maintenance_request_change_handler(body, **kwargs):
    name = body["metadata"]["name"]
    node_name = maintenance_node_name(body)
    LOG.info(f"Got node maintenance request change event {name}")
    LOG.info(
        f"The node maintenance request {name} changes are: {kwargs['diff']}"
    )
    node = kube.find(kube.Node, node_name)
    nwl = maintenance.NodeWorkloadLock.get_resource(node_name)
    nmr = maintenance.NodeMaintenanceRequest.get_resource(body)
    if not nwl.required_for_node(node):
        return

    nwl.present()

    # NOTE(vsaienko): check if current node is in maintenance to let
    # retry on Exception here.
    if not nwl.is_maintenance() and len(nwl.maintenance_locks()) >= 1:
        raise kopf.TemporaryError(
            f"Inactive NodeWorkloadLocks for openstack detected, "
            f"deferring processing for node {node.name}"
        )
    if nwl.is_active():
        nwl.set_inner_state_active()
        for service, service_class in ORDERED_SERVICES:
            if service_class.maintenance_api:
                LOG.info(
                    f"Got moving node {node_name} into maintenance for {service_class.service}"
                )
                await service_class.process_nmr(node, nmr)
                LOG.info(
                    f"The node {node_name} is ready for maintenance for {service_class.service}"
                )
    nwl.set_state_inactive()


@kopf.on.delete(*maintenance.NodeMaintenanceRequest.kopf_on_args)
async def node_maintenance_request_delete_handler(body, **kwargs):
    name = body["metadata"]["name"]
    node_name = maintenance_node_name(body)
    LOG.info(f"Got node maintenance request delete event {name}")

    node = kube.find(kube.Node, node_name)
    nwl = maintenance.NodeWorkloadLock.get_resource(node_name)
    nmr = maintenance.NodeMaintenanceRequest.get_resource(body)
    if not nwl.required_for_node(node):
        nwl.absent()
        return

    if nwl.is_maintenance():
        for service, service_class in ORDERED_SERVICES:
            if service_class.maintenance_api:
                LOG.info(
                    f"Moving node {node_name} to operational state for {service_class.service}"
                )
                await service_class.delete_nmr(node, nmr)
                LOG.info(
                    f"The node {node_name} is ready for operations for {service_class.service}"
                )
    nwl.set_inner_state_inactive()
    nwl.set_state_active()


@kopf.on.create(*maintenance.ClusterMaintenanceRequest.kopf_on_args)
@kopf.on.update(*maintenance.ClusterMaintenanceRequest.kopf_on_args)
@kopf.on.resume(*maintenance.ClusterMaintenanceRequest.kopf_on_args)
async def cluster_maintenance_request_change_handler(body, **kwargs):
    name = body["metadata"]["name"]
    LOG.info(f"Got cluster maintenance request change event {name}")
    LOG.info(
        f"The cluster maintenance request {name} changes are: {kwargs['diff']}"
    )
    if not settings.OSCTL_NODE_MAINTENANCE_ENABLED:
        return
    osdpl = kube.get_osdpl()
    if not osdpl or not osdpl.exists():
        LOG.info("Can't find OpenStackDeployment object")
        return

    osdpl_name = osdpl.metadata["name"]
    osdpl_namespace = osdpl.metadata["namespace"]
    osdplst = osdplstatus.OpenStackDeploymentStatus(
        osdpl_name, osdpl_namespace
    )
    osdplst.reload()
    osdplst_status = osdplst.get_osdpl_status()
    if osdplst_status != osdplstatus.APPLIED:
        raise kopf.TemporaryError(
            f"Waiting osdpl status APPLIED, current state is {osdplst_status}"
        )

    cwl = maintenance.ClusterWorkloadLock.get_resource(osdpl_name)

    await health.wait_services_healthy(osdpl)

    LOG.info(f"Releasing {name} ClusterWorkloadLock")
    cwl.set_state_inactive()


@kopf.on.delete(*maintenance.ClusterMaintenanceRequest.kopf_on_args)
async def cluster_maintenance_request_delete_handler(body, **kwargs):
    name = body["metadata"]["name"]
    LOG.info(f"Got cluster maintenance request delete event {name}")
    # NOTE(vsaienko): we don't care about maintenance, just ignore event.
    if not settings.OSCTL_NODE_MAINTENANCE_ENABLED:
        return

    osdpl = kube.get_osdpl()
    if not osdpl or not osdpl.exists():
        LOG.info("Can't find OpenStackDeployment object")
        return
    name = osdpl.metadata["name"]
    cwl = maintenance.ClusterWorkloadLock.get_resource(name)
    cwl.set_state_active()
