import asyncio
from dataclasses import dataclass
import logging

import pykube

from openstack_controller import constants
from openstack_controller import settings
from openstack_controller import osdplstatus

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeploymentStatusCondition:
    status: str
    type: str
    reason: str
    message: str
    lastUpdateTime: str
    lastTransitionTime: str


@dataclass(frozen=True)
class StatefulSetStatus:
    replicas: int
    observedGeneration: int = 0
    currentRevision: str = ""
    updateRevision: str = ""
    collisionCount: int = 0
    readyReplicas: int = 0
    updatedReplicas: int = 0
    currentReplicas: int = 0


@dataclass(frozen=True)
class DaemonSetStatus:
    currentNumberScheduled: int
    numberMisscheduled: int
    desiredNumberScheduled: int
    numberReady: int
    observedGeneration: int = 0
    numberAvailable: int = 0
    numberUnavailable: int = 0
    updatedNumberScheduled: int = 0


def ident(meta):
    name = meta["name"]
    application = meta.get("labels", {}).get("application", name)
    component = meta.get("labels", {}).get("component", name)

    # single out prometheus-exported Deployments
    if application.startswith("prometheus") and component == "exporter":
        application = "prometheus-exporter"
        # examples:
        # name=openstack-barbican-rabbitmq-rabbitmq-exporter
        # name=openstack-memcached-memcached-exporter
        # name=prometheus-mysql-exporter
        prefix, component, *parts = name.split("-")
        if parts[0] == "rabbitmq" and component != "rabbitmq":
            component += "-rabbitmq"
    # single out rabbitmq StatefulSets
    # examples:
    # name=openstack-nova-rabbitmq-rabbitmq
    # name=openstack-rabbitmq-rabbitmq
    elif application == "rabbitmq" and component == "server":
        prefix, service, *parts = name.split("-")
        if service != "rabbitmq":
            application = service
            component = "rabbitmq"
    else:
        # For other cases pick component name from resource name to allow multiple
        # resources per same component/application.
        # Remove redundant {applicaion}- part
        short_component_name = name.split(f"{application}-", maxsplit=1)[-1]
        if short_component_name:
            component = short_component_name

    return application, component


def set_multi_application_health(osdplst, patch):
    LOG.debug(f"Set multi application health")
    osdplst.set_osdpl_health(patch)


def is_application_ready(application, osdpl):
    osdplst = osdplstatus.OpenStackDeploymentStatus(
        osdpl.name, osdpl.namespace
    )
    osdplst.reload()

    app_status = (
        osdplst.obj.get("status", {}).get("health", {}).get(application)
    )
    if not app_status:
        LOG.info(
            f"Application: {application} is not present in .status.health."
        )
        return False
    # TODO(avolkov): this func may return false positive if not all components
    #   of an app exists in k8s, it needs to be combined with
    #   openstack_controller.services.base.Service.healthy
    elif all(
        [
            component_health["status"] == constants.OK
            for component_health in app_status.values()
        ]
    ):
        LOG.info(f"All components for application: {application} are healthy.")
        return True

    not_ready = [
        component
        for component, health in app_status.items()
        if health["status"] != "Ready"
    ]
    LOG.info(
        f"Some components for application: {application} not ready: {not_ready}"
    )
    return False


async def _wait_application_ready(
    application, osdpl, delay=settings.OSCTL_WAIT_APPLICATION_READY_DELAY
):
    i = 1
    while not is_application_ready(application, osdpl):
        LOG.info(f"Checking application {application} health, attempt: {i}")
        i += 1
        await asyncio.sleep(delay)


async def wait_application_ready(
    application,
    osdpl,
    timeout=settings.OSCTL_WAIT_APPLICATION_READY_TIMEOUT,
    delay=settings.OSCTL_WAIT_APPLICATION_READY_DELAY,
):
    LOG.info(f"Waiting for application becomes ready for {timeout}s")
    await asyncio.wait_for(
        _wait_application_ready(application, osdpl, delay=delay),
        timeout=timeout,
    )


def daemonset_health_status(obj):
    st = DaemonSetStatus(**obj["status"])
    res_health = constants.UNKNOWN
    if (
        st.currentNumberScheduled
        == st.desiredNumberScheduled
        == st.numberReady
        == st.updatedNumberScheduled
        == st.numberAvailable
    ):
        if not st.numberMisscheduled:
            res_health = constants.OK
        else:
            res_health = constants.PROGRESS
    elif st.updatedNumberScheduled < st.desiredNumberScheduled:
        res_health = constants.PROGRESS
    elif st.numberReady < st.desiredNumberScheduled:
        res_health = constants.BAD
    return res_health


def statefulset_health_status(obj):
    st = StatefulSetStatus(**obj["status"])
    res_health = constants.UNKNOWN
    if st.updateRevision:
        # updating, created new ReplicaSet
        if st.currentRevision == st.updateRevision:
            if st.replicas == st.readyReplicas == st.currentReplicas:
                res_health = constants.OK
            else:
                res_health = constants.BAD
        else:
            res_health = constants.PROGRESS
    else:
        if st.replicas == st.readyReplicas == st.currentReplicas:
            res_health = constants.OK
        else:
            res_health = constants.BAD
    return res_health


def deployment_status_conditions(conditions):
    conds = conditions or []
    return [DeploymentStatusCondition(**c) for c in conds]


def deployment_health_status(obj):
    # TODO(pas-ha) investigate if we can use status.conditions
    # just for aggroing, but derive health from other status fields
    # which are available.
    avail_cond = None
    progr_cond = None
    conds = deployment_status_conditions(obj["status"].get("conditions"))
    for c in conds:
        if c.type == "Available":
            avail_cond = c
        elif c.type == "Progressing":
            progr_cond = c
    conditions_available = avail_cond is not None and progr_cond is not None
    res_health = constants.UNKNOWN
    if conditions_available:
        if avail_cond.status == "True" and (
            progr_cond.status == "True"
            and progr_cond.reason == "NewReplicaSetAvailable"
        ):
            res_health = constants.OK
        elif avail_cond.status == "False":
            res_health = constants.BAD
        elif progr_cond.reason == "ReplicaSetUpdated":
            res_health = constants.PROGRESS
    return res_health


def health_status(obj):
    return {
        pykube.Deployment: deployment_health_status,
        pykube.DaemonSet: daemonset_health_status,
        pykube.StatefulSet: statefulset_health_status,
    }[type(obj)](obj.obj)
