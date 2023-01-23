import kopf

from openstack_controller import settings  # noqa
from openstack_controller import utils
from openstack_controller import kube
from openstack_controller import layers


LOG = utils.get_logger(__name__)


@kopf.on.resume(*kube.OpenStackDeploymentSecret.kopf_on_args)
@kopf.on.update(*kube.OpenStackDeploymentSecret.kopf_on_args)
@kopf.on.create(*kube.OpenStackDeploymentSecret.kopf_on_args)
async def handle(body, meta, spec, logger, reason, **kwargs):
    # TODO(pas-ha) remove all this kwargs[*] nonsense, accept explicit args,
    # pass further only those that are really needed
    # actual **kwargs form is for forward-compat with kopf itself
    LOG.info(f"Got osdplsecret event {reason}")
    LOG.info(f"Changes are: {kwargs['diff']}")

    spec = body["spec"]
    spec_hash = layers.spec_hash(spec)
    kwargs["patch"].setdefault("status", {})
    kwargs["patch"]["status"]["hash"] = spec_hash
    osdpl = kube.get_osdpl()
    if not osdpl:
        raise kopf.TemporaryError(
            "The OpenStackDeploument object not found. Waiting for it."
        )
    osdpl.patch({"status": {"watched": {"osdplsecret": {"hash": spec_hash}}}})

    return {"lastStatus": f"{reason}"}
