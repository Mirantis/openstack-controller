import asyncio
from dataclasses import dataclass
import logging

import kopf
from . import kube

LOG = logging.getLogger(__name__)

UNKNOWN, OK, PROGRESS, BAD = "Unknown", "Ready", "Progressing", "Unhealthy"


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
    observedGeneration: int
    replicas: int
    currentRevision: str
    updateRevision: str  # optional?
    collisionCount: int
    readyReplicas: int = 0
    updatedReplicas: int = 0
    currentReplicas: int = 0


@dataclass(frozen=True)
class DaemonSetStatus:
    currentNumberScheduled: int
    numberMisscheduled: int
    desiredNumberScheduled: int
    numberReady: int
    observedGeneration: int
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


def report_to_osdpl(namespace, status_health_patch):
    # NOTE(pas-ha): this depends on fact that there's *only one* OsDpl object
    # in the namespace, which is fine unitl we use openstack-helm
    # since it has hardcoded names for all the top-level resources it creates.
    # TODO(pas-ha) fix this whenever that assumption turns false
    osdpl = list(
        kube.OpenStackDeployment.objects(kube.api).filter(namespace=namespace)
    )
    if len(osdpl) == 1:
        osdpl[0].patch({"status": {"health": status_health_patch}})
    else:
        LOG.warning(
            f"Could not find unique OpenStackDeployment resource "
            f"in namespace {namespace}, skipping health report."
        )


def set_application_health(
    application, component, namespace, health, observed_generation
):
    patch = {
        application: {
            component: {"status": health, "generation": observed_generation,}
        }
    }
    report_to_osdpl(namespace, patch)


def is_application_ready(application, osdpl):
    osdpl = kube.OpenStackDeployment(kube.api, osdpl.obj)
    osdpl.reload()

    app_status = osdpl.obj.get("status", {}).get("health", {}).get(application)
    if not app_status:
        LOG.info(
            f"Application: {application} is not present in .status.health."
        )
        return False
    elif all(
        [
            component_health["status"] == OK
            for component_health in app_status.values()
        ]
    ):
        LOG.info(f"All components for application: {application} are healty.")
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


async def _wait_application_ready(application, osdpl, delay=10):
    i = 1
    while not is_application_ready(application, osdpl):
        LOG.info(f"Checking application {application} health, attempt: {i}")
        i += 1
        await asyncio.sleep(delay)


async def wait_application_ready(application, osdpl, timeout=300, delay=10):
    LOG.info(f"Waiting for application becomes ready for {timeout}s")
    await asyncio.wait_for(
        _wait_application_ready(application, osdpl, delay=delay),
        timeout=timeout,
    )


# NOTE(pas-ha) it turns out Deployment is sensitive to annotation changes as
# it bumps metadata.generation and status.observedGeneration on any
# change to annotations
# However, kopf stores its last handled state in the annotations
# of the resources the handler watches.
# Thus if we subscribe to whole 'status' field, we end up with infinite loop:
# kopf sees status change -> kopf handler handles this change ->
# kopf patches annotation -> status.observedGeneration bumped ->
# kopf sees status change ...
# This is why we subscribe to status.conditions only and use some
# heuristics to understand the reason of those changes.
# The drawback is that on any change to Deployment (even internal one like
# crashed pod being recreated) its revision and observedGeneration
# will be bumped as many times as there were changes in status.conditions
# until a stable state was reached.
@kopf.on.field("apps", "v1", "deployments", field="status.conditions")
async def deployments(name, namespace, meta, status, new, **kwargs):
    LOG.debug(f"Deployment {name} status.conditions is {status}")
    # TODO(pas-ha) investigate if we can use status.conditions
    # just for aggroing, but derive health from other status fields
    # which are available.
    application, component = ident(meta)
    conds = [DeploymentStatusCondition(**c) for c in new]
    for c in conds:
        if c.type == "Available":
            avail_cond = c
        elif c.type == "Progressing":
            progr_cond = c
    health = UNKNOWN
    if avail_cond.status == "True" and (
        progr_cond.status == "True"
        and progr_cond.reason == "NewReplicaSetAvailable"
    ):
        health = OK
    elif avail_cond.status == "False":
        health = BAD
    elif progr_cond.reason == "ReplicaSetUpdated":
        health = PROGRESS
    set_application_health(
        application, component, namespace, health, status["observedGeneration"]
    )


@kopf.on.field("apps", "v1", "statefulsets", field="status")
async def statefulsets(name, namespace, meta, status, **kwargs):
    LOG.debug(f"StatefulSet {name} status is {status}")
    application, component = ident(meta)
    st = StatefulSetStatus(**status)
    health = UNKNOWN
    if st.updateRevision:
        # updating, created new ReplicaSet
        if st.currentRevision == st.updateRevision:
            if st.replicas == st.readyReplicas == st.currentReplicas:
                health = OK
            else:
                health = BAD
        else:
            health = PROGRESS
    else:
        if st.replicas == st.readyReplicas == st.currentReplicas:
            health = OK
        else:
            health = BAD
    set_application_health(
        application, component, namespace, health, status["observedGeneration"]
    )


@kopf.on.field("apps", "v1", "daemonsets", field="status")
async def daemonsets(name, namespace, meta, status, **kwargs):
    LOG.debug(f"DaemonSet {name} status is {status}")
    application, component = ident(meta)

    st = DaemonSetStatus(**status)
    health = UNKNOWN
    if (
        st.currentNumberScheduled
        == st.desiredNumberScheduled
        == st.numberReady
        == st.updatedNumberScheduled
        == st.numberAvailable
    ):
        if not st.numberMisscheduled:
            health = OK
        else:
            health = PROGRESS
    elif st.updatedNumberScheduled < st.desiredNumberScheduled:
        health = PROGRESS
    elif st.numberReady < st.desiredNumberScheduled:
        health = BAD
    set_application_health(
        application, component, namespace, health, status["observedGeneration"]
    )


async def _delete(kind, meta):
    LOG.info(f"Handling delete event for {kind}")
    name = meta["name"]
    namespace = meta["namespace"]
    application, component = ident(meta)
    patch = {application: {component: None}}
    LOG.debug(f"Cleaning health for {kind} {name}")
    report_to_osdpl(namespace, patch)


# NOTE(vsaienko): for unknown reason when using optional=True, which have to
# prevent kopf from adding finalizer to the object, prevent kopf from handling
# delete event. Add finalizers here should be ok as we do not expect deployment
# changes on helmbundle level directly.
@kopf.on.delete("apps", "v1", "daemonsets")
async def delete_daemonset(name, meta, **kwargs):
    await _delete("DaemonSet", meta)


@kopf.on.delete("apps", "v1", "deployments")
async def delete_deployment(name, meta, **kwargs):
    await _delete("Deployment", meta)


@kopf.on.delete("apps", "v1", "statefulsets")
async def delete_statefulset(name, meta, **kwargs):
    await _delete("StatefulSet", meta)
