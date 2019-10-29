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


async def process_osdpl_event(body, meta, spec, logger, **kwargs):
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
        if event == "resume":
            if not service_instance.is_identifier_changed:
                LOG.info(
                    f"Got fake resume event for osdpl {meta['name']}, service: {service}"
                )
                continue
        service_fns[service] = service_instance.apply
    service_fns.update(
        {
            f"{s}_delete": services.registry[s](body, logger).delete
            for s in delete
        }
    )
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "created" if event == "create" else "updated"}
    else:
        return {"message": "skipped"}


@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
async def create(body, meta, spec, logger, **kwargs):
    return await process_osdpl_event(body, meta, spec, logger, **kwargs)


@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
async def update(body, meta, spec, logger, **kwargs):
    return await process_osdpl_event(body, meta, spec, logger, **kwargs)


@kopf.on.resume(*kube.OpenStackDeployment.kopf_on_args)
async def resume(body, meta, spec, logger, **kwargs):
    return await process_osdpl_event(body, meta, spec, logger, **kwargs)


@kopf.on.delete(*kube.OpenStackDeployment.kopf_on_args)
async def delete(meta, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    LOG.info(f"deleting {meta['name']}")
