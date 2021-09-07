import collections

import pykube

from openstack_controller import health
from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import utils
from openstack_controller import osdplstatus


LOG = utils.get_logger(__name__)


def get_k8s_objects(
    namespace, types=[pykube.Deployment, pykube.DaemonSet, pykube.StatefulSet]
):
    for t in types:
        for i in kube.resource_list(t, "", namespace):
            yield i


def calculate_status(k8s_object):
    ident = health.ident(k8s_object.metadata)
    health_status = health.health_status(k8s_object)
    return (
        ident,
        (
            health_status,
            utils.get_in(k8s_object.obj, ["status", "observedGeneration"], 0),
        ),
    )


def calculate_statuses(k8s_objects):
    return {k: v for k, v in (calculate_status(i) for i in k8s_objects)}


def get_health_statuses(osdpl):
    if osdpl is None:
        osdpl = kube.get_osdpl(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)
    statuses = calculate_statuses(get_k8s_objects(osdpl.namespace))
    health_all = collections.defaultdict(dict)
    for ident, status in statuses.items():
        LOG.debug(f"Got status {status} for {ident}")
        health_all[ident[0]][ident[1]] = {
            "status": status[0],
            "generation": status[1],
        }
    return health_all


def update_health_statuses():
    osdpl = kube.get_osdpl(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)
    osdplst = osdplstatus.OpenStackDeploymentStatus(
        osdpl.name, osdpl.namespace
    )
    statuses = get_health_statuses(osdpl)
    health.set_multi_application_health(osdpl, statuses, osdplst)
    LOG.info("Health statuses updated %d", len(statuses))
