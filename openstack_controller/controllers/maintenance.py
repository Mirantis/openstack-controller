import asyncio

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
SERVICE_ORDER = {"compute": 100, "networking": 120}
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
        msg = (
            f"Inactive NodeWorkloadLocks for openstack detected, "
            f"deferring processing for node {node.name}"
        )
        nwl.set_error_message(msg)
        raise kopf.TemporaryError(msg)

    osdpl = kube.get_osdpl()
    if not osdpl or not osdpl.exists():
        LOG.info("Can't find OpenStackDeployment object")
        return

    if nwl.is_active():
        nwl.set_inner_state_active()
        for service, service_class in ORDERED_SERVICES:
            service = service_class(osdpl.obj, LOG, {})
            if service.maintenance_api:
                LOG.info(
                    f"Got moving node {node_name} into maintenance for {service_class.service}"
                )
                await service.process_nmr(node, nmr)
                LOG.info(
                    f"The node {node_name} is ready for maintenance for {service_class.service}"
                )
    nwl.set_state_inactive()
    LOG.info(f"Released NodeWorkloadLock for node {node_name}")


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

    osdpl = kube.get_osdpl()
    if not osdpl or not osdpl.exists():
        LOG.info("Can't find OpenStackDeployment object")
        return

    if nwl.is_maintenance():
        LOG.info(f"Waiting for {node.name} is ready.")
        while True:
            if not node.ready:
                LOG.info(f"The node {node.name} is not ready yet.")
                await asyncio.sleep(10)
                continue
            LOG.info(f"The node {node.name} is ready.")
            break

        while True:
            LOG.info(f"Waiting for pods ready on node {node.name}.")
            node_pods = node.get_pods(namespace=osdpl.namespace)
            not_ready_pods = [
                pod.name
                for pod in node_pods
                if not pod.job_child and not pod.ready
            ]
            if not_ready_pods:
                LOG.info(f"The pods {not_ready_pods} are not ready.")
                await asyncio.sleep(10)
                continue
            LOG.info(f"All pods are ready on node {node.name}.")
            break

        for service, service_class in reversed(ORDERED_SERVICES):
            service = service_class(osdpl.obj, LOG, {})
            if service.maintenance_api:
                LOG.info(
                    f"Moving node {node_name} to operational state for {service_class.service}"
                )
                await service.delete_nmr(node, nmr)
                LOG.info(
                    f"The node {node_name} is ready for operations for {service_class.service}"
                )
    nwl.set_inner_state_inactive()
    nwl.set_state_active()
    LOG.info(f"Acquired NodeWorkloadLock for node {node_name}")


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
    osdplst_status = osdplst.get_osdpl_status()
    cwl = maintenance.ClusterWorkloadLock.get_resource(osdpl_name)
    if osdplst_status != osdplstatus.APPLIED:
        msg = (
            f"Waiting osdpl status APPLIED, current state is {osdplst_status}"
        )
        cwl.set_error_message(msg)
        raise kopf.TemporaryError(msg)

    if not cwl.is_active():
        # NOTE(vsaienko): we are in maintenance, but controller is restarted, do
        # not wait for health
        return
    cwl.set_error_message("Waiting for all OpenStack services are healthy.")
    await health.wait_services_healthy(osdpl)

    cwl.set_state_inactive()
    cwl.unset_error_message()
    LOG.info(f"Released {name} ClusterWorkloadLock")


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
    LOG.info(f"Acquired ClusterWorkloadLock {name}")
