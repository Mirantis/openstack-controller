import functools

import kopf

from . import kube
from . import layers


# TODO(pas-ha) enable debug logging


async def delete_service(service, *, body, meta, spec, logger, **kwargs):
    logger.info(f"Deleting config for {service}")
    data = layers.render_all(service, body, meta, spec, logger)
    kopf.adopt(data, body)

    # delete the object, already non-existing are auto-handled
    obj = kube.resource(data)
    obj.delete(propagation_policy="Foreground")
    logger.info(f"{obj.kind} {obj.namespace}/{obj.name} deleted")
    # remove child reference from status
    osdpl = kube.find_osdpl(meta["name"], namespace=meta["namespace"])
    status_patch = {"children": {obj.name: None}}
    osdpl.patch({"status": status_patch})
    kopf.info(
        body, reason="Delete", message=f"deleted {obj.kind} for {service}"
    )


async def apply_service(service, *, body, meta, spec, logger, event, **kwargs):
    logger.info(f"Applying config for {service}")
    data = layers.render_all(service, body, meta, spec, logger)
    # NOTE(pas-ha) this sets the parent refs in child to point to our resource
    # so that cascading delete is handled by K8s itself
    kopf.adopt(data, body)
    # apply state of the object
    obj = kube.resource(data)
    if obj.exists():
        obj.reload()
        obj.set_obj(data)
        obj.update()
        logger.debug(f"{obj.kind} child is updated: %s", obj.obj)
    else:
        obj.create()
        logger.debug(f"{obj.kind} child is created: %s", obj.obj)
    # ensure child ref exists in the status
    osdpl = kube.find_osdpl(meta["name"], namespace=meta["namespace"])
    if obj.name not in osdpl.obj.get("status", {}).get("children", {}):
        status_patch = {"children": {obj.name: "Unknown"}}
        osdpl.patch({"status": status_patch})
    kopf.info(
        body,
        reason=event.capitalize(),
        message=f"{event}d {obj.kind} for {service}",
    )


@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
async def create(body, meta, spec, logger, **kwargs):
    create, delete = layers.services(spec, logger, **kwargs)
    service_fns = {
        s: functools.partial(apply_service, service=s) for s in create
    }
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "created"}
    else:
        return {"message": "skipped"}


@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
async def update(body, meta, spec, logger, **kwargs):
    update, delete = layers.services(spec, logger, **kwargs)
    if delete:
        logger.info(f"deleting children {' '.join(delete)}")
    service_fns = {
        s: functools.partial(apply_service, service=s) for s in update
    }
    for service in delete:
        service_fns[service + "_delete"] = functools.partial(
            delete_service, service=service
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
