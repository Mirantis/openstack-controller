import asyncio

import kopf

from . import kube
from . import layers
from . import openstack
from . import services
from . import version

from mcp_k8s_lib import utils


LOG = utils.get_logger(__name__)


def update_status(body, patch):
    osdpl = kube.OpenStackDeployment(kube.api, body)
    osdpl.patch({"status": patch})


@kopf.on.resume(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
async def apply(body, meta, spec, logger, event, **kwargs):
    event = kwargs["cause"].event
    namespace = meta["namespace"]
    LOG.info(f"Got osdpl event {event}")
    if spec["draft"]:
        LOG.info("OpenStack deployment is in draft mode, skipping handling...")
        return

    # TODO(e0ne): change create_admin_credentials once kube.save_secret_data
    # won't update secrets
    openstack.get_or_create_admin_credentials(namespace)
    kube.wait_for_secret(namespace, openstack.ADMIN_SECRET_NAME)

    fingerprint = layers.spec_hash(body["spec"])
    version_patch = {
        "version": version.release_string,
        "fingerprint": fingerprint,
    }

    update_status(body, version_patch)

    update, delete = layers.services(spec, logger, **kwargs)

    task_def = {}
    for service in update:
        service_instance = services.registry[service](body, logger)
        task_def[
            asyncio.create_task(
                service_instance.apply(
                    event=event,
                    body=body,
                    meta=meta,
                    spec=spec,
                    logger=logger,
                    **kwargs,
                )
            )
        ] = (service_instance.apply, event, body, meta, spec, logger, kwargs)

    if delete:
        LOG.info(f"deleting children {' '.join(delete)}")
    for service in delete:
        service_instance = services.registry[service](body, logger)
        task_def[
            asyncio.create_task(
                service_instance.delete(
                    body=body, meta=meta, spec=spec, logger=logger, **kwargs
                )
            )
        ] = (service_instance.delete, event, body, meta, spec, logger, kwargs)
    while task_def:
        # NOTE(e0ne): we can switch to asyncio.as_completed to run tasks
        # faster if needed.
        done, _ = await asyncio.wait(task_def.keys())
        for task in done:
            coro, event, body, meta, spec, logger, kwargs = task_def.pop(task)
            if isinstance(task.exception(), kopf.HandlerRetryError):
                task_def[
                    asyncio.create_task(
                        coro(
                            event=event,
                            body=body,
                            meta=meta,
                            spec=spec,
                            logger=logger,
                            **kwargs,
                        )
                    )
                ] = (coro, event, body, meta, spec, logger, kwargs)
        # Let's wait for 10 second before retry to not introduce a lot of
        # task scheduling in case of some depended task is slow.
        await asyncio.sleep(10)

    return {"lastStatus": f"{event}d"}


@kopf.on.delete(*kube.OpenStackDeployment.kopf_on_args)
async def delete(name, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    # TODO(pas-ha) remove secrets and so on?
    LOG.info(f"deleting {name}")
