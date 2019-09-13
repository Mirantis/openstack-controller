import kopf

from . import kube
from . import layers
from . import openstack
from . import services

# TODO(pas-ha) enable debug logging


@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
async def create(body, meta, spec, logger, **kwargs):
    # TODO(e0ne): change create_admin_credentials once kube.save_secret_data
    # won't update secrets
    openstack.get_or_create_admin_credentials(meta["namespace"])
    kube.wait_for_secret(meta["namespace"], openstack.ADMIN_SECRET_NAME)

    create, delete = layers.services(spec, logger, **kwargs)
    service_fns = {s: services.registry[s](body, logger).apply for s in create}
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "created"}
    else:
        return {"message": "skipped"}


@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
async def update(body, meta, spec, logger, **kwargs):
    # TODO(e0ne): change create_admin_credentials once kube.save_secret_data
    # won't update secrets
    openstack.get_or_create_admin_credentials(meta["namespace"])
    kube.wait_for_secret(meta["namespace"], openstack.ADMIN_SECRET_NAME)

    update, delete = layers.services(spec, logger, **kwargs)
    if delete:
        logger.info(f"deleting children {' '.join(delete)}")
    service_fns = {s: services.registry[s](body, logger).apply for s in update}
    service_fns.update(
        {
            f"{s}_delete": services.registry[s](body, logger).delete
            for s in delete
        }
    )
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "updated"}
    else:
        return {"message": "skipped"}


@kopf.on.delete(*kube.OpenStackDeployment.kopf_on_args)
async def delete(meta, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    logger.info(f"deleting {meta['name']}")
