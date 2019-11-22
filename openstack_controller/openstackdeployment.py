import kopf

from . import kube
from . import layers
from . import openstack
from . import services
from . import version

from mcp_k8s_lib import utils


LOG = utils.get_logger(__name__)


async def update_status(body, patch):
    osdpl = kube.OpenStackDeployment(kube.api, body)
    osdpl.patch({"status": patch})


@kopf.on.resume(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
async def apply(body, meta, spec, logger, event, **kwargs):
    event = kwargs["cause"].event
    namespace = meta["namespace"]
    LOG.info(f"Got osdpl event {event}")
    # TODO(e0ne): change create_admin_credentials once kube.save_secret_data
    # won't update secrets
    openstack.get_or_create_admin_credentials(namespace)
    kube.wait_for_secret(namespace, openstack.ADMIN_SECRET_NAME)

    fingerprint = layers.spec_hash(body)
    version_patch = {
        "version": version.release_string,
        "fingerprint": fingerprint,
    }
    await update_status(body, version_patch)

    update, delete = layers.services(spec, logger, **kwargs)

    if delete:
        LOG.info(f"deleting children {' '.join(delete)}")
    service_fns = {}
    for service in update:
        service_instance = services.registry[service](body, logger)
        service_fns[service] = service_instance.apply
    service_fns.update(
        {
            f"{s}_delete": services.registry[s](body, logger).delete
            for s in delete
        }
    )
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"lastStatus": f"{event}d"}
    else:
        return {"lastStatus": "{event} skipped"}


@kopf.on.delete(*kube.OpenStackDeployment.kopf_on_args)
async def delete(name, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    # TODO(pas-ha) remove secrets and so on?
    LOG.info(f"deleting {name}")
