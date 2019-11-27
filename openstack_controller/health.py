from dataclasses import dataclass
import logging

import kopf
from . import kube

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeplCondition:
    status: str
    type: str
    reason: str
    message: str
    lastUpdateTime: str
    lastTransitionTime: str


@dataclass(frozen=True)
class StsStatus:
    observedGeneration: int
    replicas: int
    readyReplicas: int
    currentRevision: str
    updateRevision: str  # optional?
    collisionCount: int
    updatedReplicas: int = 0
    currentReplicas: int = 0


@dataclass(frozen=True)
class DsStatus:
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
    # NOTE(pas-ha): this depends on fact that there"s *only one* OsDpl object
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


@kopf.on.field("apps", "v1", "deployments", field="status.conditions")
async def deployments(name, namespace, meta, status, new, **kwargs):
    LOG.debug(f"Deployment {name} status.conditions is {status}")
    # TODO(pas-ha) investigate if we can use status.conditions
    # just for aggroing, but derive health from other status fields
    # which are available.
    application, component = ident(meta)
    conds = [DeplCondition(**c) for c in new]
    for c in conds:
        if c.type == "Available":
            avail_cond = c
        elif c.type == "Progressing":
            progr_cond = c
    health = "Unknown"
    if avail_cond.status == "True" and (
        progr_cond.status == "True"
        and progr_cond.reason == "NewReplicaSetAvailable"
    ):
        health = "Ready"
    elif avail_cond.status == "False":
        health = "Unhealthy"
    elif progr_cond.reason == "ReplicaSetUpdated":
        health = "Progressing"
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
    st = StsStatus(**status)
    health = "Unknown"
    if st.updateRevision:
        # updating, created new ReplicaSet
        if st.currentRevision == st.updateRevision:
            if st.replicas == st.readyReplicas == st.currentReplicas:
                health = "Ready"
            else:
                health = "Unhealthy"
        else:
            health = "Progressing"
    else:
        if st.replicas == st.readyReplicas == st.currentReplicas:
            health = "Ready"
        else:
            health = "Unhealthy"
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
    st = DsStatus(**status)
    health = "Unknown"
    if (
        st.currentNumberScheduled
        == st.desiredNumberScheduled
        == st.numberReady
        == st.updatedNumberScheduled
        == st.numberAvailable
    ):
        if not st.numberMisscheduled:
            health = "Ready"
        else:
            health = "Progressing"
    elif st.updatedNumberScheduled < st.desiredNumberScheduled:
        health = "Progressing"
    elif st.numberReady < st.desiredNumberScheduled:
        health = "Unhealthy"
    patch = {
        application: {
            component: {
                "status": health,
                "generation": status["observedGeneration"],
            }
        }
    }
    report_to_osdpl(namespace, patch)
