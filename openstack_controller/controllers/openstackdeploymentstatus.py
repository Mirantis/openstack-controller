import kopf

from openstack_controller import settings  # noqa
from openstack_controller import utils
from openstack_controller import osdplstatus


LOG = utils.get_logger(__name__)


# on.field to force storing that field to be reacting on its changes
@kopf.on.field(
    *osdplstatus.OpenStackDeploymentStatus.kopf_on_args, field="status"
)
@kopf.on.resume(*osdplstatus.OpenStackDeploymentStatus.kopf_on_args)
@kopf.on.update(*osdplstatus.OpenStackDeploymentStatus.kopf_on_args)
@kopf.on.create(*osdplstatus.OpenStackDeploymentStatus.kopf_on_args)
async def handle(body, meta, spec, logger, reason, **kwargs):
    # TODO(pas-ha) remove all this kwargs[*] nonsense, accept explicit args,
    # pass further only those that are really needed
    # actual **kwargs form is for forward-compat with kopf itself
    LOG.info(f"Got osdplstatus event {reason}")
    LOG.info(f"Changes are: {kwargs['diff']}")
    return {"lastStatus": f"{reason}"}


@kopf.on.field(
    *osdplstatus.OpenStackDeploymentStatus.kopf_on_args,
    field="status.services",
)
@kopf.on.resume(*osdplstatus.OpenStackDeploymentStatus.kopf_on_args)
async def osdplst_status_services(
    name, namespace, body, meta, spec, logger, reason, **kwargs
):
    LOG.info(f"Got osdplstatus status.services event {reason}")
    LOG.info(f"Changes are: {kwargs['diff']}")
    osdplst = osdplstatus.OpenStackDeploymentStatus(name, namespace)
    if not osdplst.exists():
        return
    osdplst.update_osdpl_lcm_progress()
    return {"lastStatus": f"{reason}"}
