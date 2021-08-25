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
@utils.collect_handler_metrics
async def handle(body, meta, spec, logger, event, **kwargs):
    # TODO(pas-ha) "cause" is deprecated, replace with "reason"
    event = kwargs["cause"].event
    # TODO(pas-ha) remove all this kwargs[*] nonsense, accept explicit args,
    # pass further only those that are really needed
    # actual **kwargs form is for forward-compat with kopf itself
    LOG.info(f"Got osdplstatus event {event}")
    LOG.info(f"Changes are: {kwargs['diff']}")
    return {"lastStatus": f"{event}"}
