import kopf
from mcp_k8s_lib import utils

from openstack_controller import constants
from openstack_controller import health
from openstack_controller import settings

LOG = utils.get_logger(__name__)

kopf.config.WatchersConfig.default_stream_timeout = (
    settings.KOPF_WATCH_STREAM_TIMEOUT
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
    application, component = health.ident(meta)
    conds = [health.DeploymentStatusCondition(**c) for c in new]
    for c in conds:
        if c.type == "Available":
            avail_cond = c
        elif c.type == "Progressing":
            progr_cond = c
    res_health = constants.UNKNOWN
    if avail_cond.status == "True" and (
        progr_cond.status == "True"
        and progr_cond.reason == "NewReplicaSetAvailable"
    ):
        res_health = constants.OK
    elif avail_cond.status == "False":
        res_health = constants.BAD
    elif progr_cond.reason == "ReplicaSetUpdated":
        res_health = constants.PROGRESS
    health.set_application_health(
        application,
        component,
        namespace,
        res_health,
        status["observedGeneration"],
    )


@kopf.on.field("apps", "v1", "statefulsets", field="status")
async def statefulsets(name, namespace, meta, status, **kwargs):
    LOG.debug(f"StatefulSet {name} status is {status}")
    application, component = health.ident(meta)
    st = health.StatefulSetStatus(**status)
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
    health.set_application_health(
        application,
        component,
        namespace,
        res_health,
        status["observedGeneration"],
    )


@kopf.on.field("apps", "v1", "daemonsets", field="status")
async def daemonsets(name, namespace, meta, status, **kwargs):
    LOG.debug(f"DaemonSet {name} status is {status}")
    application, component = health.ident(meta)

    st = health.DaemonSetStatus(**status)
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
    health.set_application_health(
        application,
        component,
        namespace,
        res_health,
        status["observedGeneration"],
    )


async def _delete(kind, meta):
    LOG.info(f"Handling delete event for {kind}")
    name = meta["name"]
    namespace = meta["namespace"]
    application, component = health.ident(meta)
    patch = {application: {component: None}}
    LOG.debug(f"Cleaning health for {kind} {name}")
    health.report_to_osdpl(namespace, patch)


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
