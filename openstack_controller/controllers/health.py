import kopf
from mcp_k8s_lib import utils as mcp_utils

from openstack_controller import constants
from openstack_controller import health
from openstack_controller import hooks
from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import utils


LOG = mcp_utils.get_logger(__name__)

# DAEMONSET_HOOKS format
# {(transition state from, transition state to):
#    {application-component: func to be called}}
# node added in two transitions:
# 1. from Ready to Unhealthy
# 2. Unhealthy to Ready
# node removed in two transitions:
# 1. from Ready to Progressing
# 2. from Progressing to Ready
DAEMONSET_HOOKS = {
    (constants.BAD, constants.OK): {
        "nova-compute-default": hooks.nova_daemonset_created
    },
}

kopf.config.WatchersConfig.default_stream_timeout = (
    settings.KOPF_WATCH_STREAM_TIMEOUT
)


def get_osdpl(namespace):
    osdpl = list(
        kube.OpenStackDeployment.objects(kube.api).filter(namespace=namespace)
    )
    if len(osdpl) != 1:
        LOG.warning(
            f"Could not find unique OpenStackDeployment resource "
            f"in namespace {namespace}, skipping health report processing."
        )
        return
    return osdpl[0]


def _delete(osdpl, kind, meta, application, component):
    LOG.info(f"Handling delete event for {kind}")
    name = meta["name"]
    namespace = meta["namespace"]
    LOG.debug(f"Cleaning health for {kind} {name}")
    health.set_application_health(
        osdpl, application, component, namespace, None, None
    )


# NOTE(vsaienko): for unknown reason when using optional=True, which have to
# prevent kopf from adding finalizer to the object, prevent kopf from handling
# delete event. Add finalizers here should be ok as we do not expect deployment
# changes on helmbundle level directly.

# NOTE(pas-ha) not using separate handler for delete
# seems like similar troubles with status bumps on metadata changes
# happen at least to StatefulSets as well (see below)
# Adding deletion timestamp to StatefulSet bumps the observedGeneration
# in the status, and thus the on.status handler reacts, not on.delete,
# which does not remove the finalizer.
# better let kopf's handler deduplicaiton handle it, and
# manually discern what to do in a single handler.

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
@kopf.on.delete("apps", "v1", "deployments")
async def deployments(name, namespace, meta, status, new, event, **kwargs):
    osdpl = get_osdpl(namespace)
    if not osdpl:
        return
    application, component = health.ident(meta)
    if event == "delete":
        _delete(osdpl, "Deployment", meta, application, component)
        return
    LOG.debug(f"Deployment {name} status.conditions is {status}")
    # TODO(pas-ha) investigate if we can use status.conditions
    # just for aggroing, but derive health from other status fields
    # which are available.
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
        osdpl,
        application,
        component,
        namespace,
        res_health,
        status["observedGeneration"],
    )


@kopf.on.field("apps", "v1", "statefulsets", field="status")
@kopf.on.delete("apps", "v1", "statefulsets")
async def statefulsets(name, namespace, meta, status, event, **kwargs):
    osdpl = get_osdpl(namespace)
    if not osdpl:
        return
    application, component = health.ident(meta)
    if event == "delete":
        _delete(osdpl, "StatefulSet", meta, application, component)
        return
    LOG.debug(f"StatefulSet {name} status is {status}")
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
        osdpl,
        application,
        component,
        namespace,
        res_health,
        status["observedGeneration"],
    )


@kopf.on.field("apps", "v1", "daemonsets", field="status")
@kopf.on.delete("apps", "v1", "daemonsets")
async def daemonsets(name, namespace, meta, status, event, **kwargs):
    LOG.debug(f"DaemonSet {name} status is {status}")
    osdpl = get_osdpl(namespace)
    if not osdpl:
        return
    application, component = health.ident(meta)
    if event == "delete":
        _delete(osdpl, "DaemonSet", meta, application, component)
        return
    LOG.debug(f"DaemonSet {name} status is {status}")
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
    prev_res_health = utils.get_in(
        osdpl.obj,
        ["status", "health", application, component],
        {"status": ""},
    )
    LOG.debug(
        f"Daemonset {application}-{component} state transition from {prev_res_health['status']} to {res_health}"
    )
    hook = utils.get_in(
        DAEMONSET_HOOKS,
        [
            (prev_res_health["status"], res_health),
            f"{application}-{component}",
        ],
    )
    kwargs["OK_desiredNumberScheduled"] = prev_res_health.get(
        "OK_desiredNumberScheduled", 0
    )
    if hook:
        await hook(osdpl, name, namespace, meta, **kwargs)
    health.set_application_health(
        osdpl,
        application,
        component,
        namespace,
        res_health,
        status["observedGeneration"],
        {"OK_desiredNumberScheduled": st.desiredNumberScheduled}
        if res_health == constants.OK
        else {},
    )
