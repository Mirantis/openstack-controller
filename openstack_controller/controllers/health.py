import kopf

from openstack_controller import batch_health
from openstack_controller import constants
from openstack_controller import health
from openstack_controller import hooks
from openstack_controller import kube
from openstack_controller import settings  # noqa
from openstack_controller import utils


LOG = utils.get_logger(__name__)

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
        "nova-compute-default": hooks.run_nova_cell_setup
    },
    (constants.BAD, constants.OK): {
        "octavia-health-manager-default": hooks.run_octavia_create_resources
    },
}


def _delete(osdpl, kind, meta, application, component):
    LOG.info(f"Handling delete event for {kind}")
    name = meta["name"]
    LOG.debug(f"Cleaning health for {kind} {name}")
    osdpl.patch({"status": {"health": {application: {component: None}}}})


@kopf.on.delete("apps", "v1", "deployments")
async def deployments(name, namespace, meta, status, new, event, **kwargs):
    LOG.debug(f"Deployment {name} status.conditions is {status}")
    osdpl = health.get_osdpl(namespace)
    if not osdpl:
        return
    application, component = health.ident(meta)
    _delete(osdpl, "Deployment", meta, application, component)


@kopf.on.delete("apps", "v1", "statefulsets")
async def statefulsets(name, namespace, meta, status, event, **kwargs):
    LOG.debug(f"StatefulSet {name} status is {status}")
    osdpl = health.get_osdpl(namespace)
    if not osdpl:
        return
    application, component = health.ident(meta)
    _delete(osdpl, "StatefulSet", meta, application, component)


@kopf.on.field("apps", "v1", "daemonsets", field="status")
@kopf.on.delete("apps", "v1", "daemonsets")
async def daemonsets(name, namespace, meta, status, event, **kwargs):
    LOG.debug(f"DaemonSet {name} status is {status}")
    osdpl = health.get_osdpl(namespace)
    if not osdpl:
        return
    application, component = health.ident(meta)
    if event == "delete":
        _delete(osdpl, "DaemonSet", meta, application, component)
        return
    res_health = health.daemonset_health_status(kwargs["body"])
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
        LOG.debug(f"Daemonset {application}-{component} awaiting hook")
        await hook(osdpl, name, namespace, meta, **kwargs)


@kopf.daemon(*kube.OpenStackDeployment.kopf_on_args)
def batch_health_updater(stopped, **kwargs):
    LOG.info("Batch health updater started")
    while not stopped:
        batch_health.update_health_statuses()
        stopped.wait(settings.OSCTL_BATCH_HEATH_UPDATER_PERIOD)
