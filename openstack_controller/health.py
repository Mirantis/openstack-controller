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
    readyReplicas: int
    currentRevision: str
    updateRevision: str  # optional?
    collisionCount: int
    updatedReplicas: int = 0
    currentReplicas: int = 0


@dataclass(frozen=True)
class DaemonSetStatus:
    currentNumberScheduled: int
    numberMisscheduled: int
    desiredNumberScheduled: int
    numberReady: int
    observedGeneration: int
    numberAvailable: int
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
    # single out openvswitch DaemonSets
    elif application == "openvswitch":
        # example:
        # name=openvswitch-db component=openvswitch-vswitchd-db
        component = "-".join(component.split("-")[1:])

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
    patch = {
        application: {
            component: {
                "status": health,
                "generation": status["observedGeneration"],
            }
        }
    }
    report_to_osdpl(namespace, patch)


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
    patch = {
        application: {
            component: {
                "status": health,
                "generation": status["observedGeneration"],
            }
        }
    }
    report_to_osdpl(namespace, patch)


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
    patch = {
        application: {
            component: {
                "status": health,
                "generation": status["observedGeneration"],
            }
        }
    }
    report_to_osdpl(namespace, patch)
