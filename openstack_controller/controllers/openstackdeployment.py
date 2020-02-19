import asyncio
import copy

import kopf

from openstack_controller import exception
from openstack_controller import cache
from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import layers
from openstack_controller import secrets
from openstack_controller import services
from openstack_controller import settings
from openstack_controller import version

from mcp_k8s_lib import utils


LOG = utils.get_logger(__name__)

kopf.config.WatchersConfig.default_stream_timeout = (
    settings.KOPF_WATCH_STREAM_TIMEOUT
)


def update_status(body, patch):
    osdpl = kube.OpenStackDeployment(kube.api, body)
    osdpl.patch({"status": patch})


def is_openstack_version_changed(diff):
    for diff_item in diff:
        if diff_item.field == ("spec", "openstack_version"):
            return True


def get_os_services_for_upgrade(enabled_services):
    return [
        service
        for service in constants.OPENSTACK_SERVICES_UPGRADE_ORDER
        if service in enabled_services
    ]


async def run_task(task_def):
    """ Run OpenStack controller tasks

    Runs tasks passed as `task_def` with implementing the following logic:

    * In case of permanent error retry all the tasks that finished with
      TemporaryError and fail permanently.

    * In case of unknown error retry all the tasks that finished with
      TemporaryError and raise TaskException. In this case kpof will
      retry whole handler by default.

    :param task_def: Dictionary with the task definitision.
    :raises: kopf.PermanentError when permanent error occured.
    :raises: TaskException when unknown exception occured.
    """

    permanent_exception = None
    unknown_exception = None

    while task_def:
        # NOTE(e0ne): we can switch to asyncio.as_completed to run tasks
        # faster if needed.
        done, _ = await asyncio.wait(task_def.keys())
        for task in done:
            coro, event, body, meta, spec, logger, kwargs = task_def.pop(task)
            if task.exception():
                if isinstance(task.exception(), kopf.TemporaryError):
                    LOG.warning(
                        f"Got retriable exception when applying {coro}, retrying..."
                    )
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
                    LOG.debug(task.print_stack())
                elif isinstance(task.exception(), kopf.PermanentError):
                    LOG.error(f"Failed to apply {coro} permanently.")
                    LOG.error(task.print_stack())
                    permanent_exception = kopf.PermanentError(
                        "Permanent error occured."
                    )
                else:
                    LOG.warning(
                        f"Got unknown exception while applying {coro}."
                    )
                    LOG.warning(task.print_stack())
                    unknown_exception = exception.TaskException(
                        "Unknown error occured."
                    )
        # Let's wait for 10 second before retry to not introduce a lot of
        # task scheduling in case of some depended task is slow.
        await asyncio.sleep(10)

    if permanent_exception:
        raise permanent_exception
    if unknown_exception:
        # NOTE(vsaienko): raise unknown for kopf to keep default exception retry behaviour
        # https://github.com/zalando-incubator/kopf/blob/351bf5/docs/errors.rst#regular-errors
        raise unknown_exception


def discover_images(body, logger):
    osdpl = layers.merge_spec(copy.deepcopy(body)["spec"], logger)

    cache_images = set(layers.render_cache_images() or [])
    images = {}
    for name, url in layers.render_artifacts(osdpl).items():
        images.setdefault(url, []).append(name)
    return {
        names[0].replace("_", "-"): url
        for url, names in images.items()
        if set(names) & cache_images
    }


@kopf.on.resume(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
async def apply(body, meta, spec, logger, event, **kwargs):
    event = kwargs["cause"].event
    namespace = meta["namespace"]
    LOG.info(f"Got osdpl event {event}")
    if spec["draft"]:
        LOG.info("OpenStack deployment is in draft mode, skipping handling...")
        return {"lastStatus": f"{event} drafted"}

    # TODO(e0ne): change to use 'create' method once kube.save_secret_data
    # won't update secrets
    secrets.OpenStackAdminSecret(namespace).ensure()
    kube.wait_for_secret(namespace, constants.ADMIN_SECRET_NAME)

    fingerprint = layers.spec_hash(body["spec"])
    version_patch = {
        "version": version.release_string,
        "fingerprint": fingerprint,
    }

    update_status(body, version_patch)

    images = discover_images(body, logger)
    if images != await cache.images(meta["namespace"]):
        await cache.restart(images, body)
    await cache.wait_ready(meta["namespace"])

    update, delete = layers.services(spec, logger, **kwargs)

    if is_openstack_version_changed(kwargs["diff"]):
        services_to_upgrade = get_os_services_for_upgrade(update)
        LOG.info(
            f"Starting upgrade for the following services: {services_to_upgrade}"
        )
        for service in services_to_upgrade:
            task_def = {}
            service_instance = services.registry[service](body, logger)
            task_def[
                asyncio.create_task(
                    service_instance.upgrade(
                        event=event,
                        body=body,
                        meta=meta,
                        spec=spec,
                        logger=logger,
                        **kwargs,
                    )
                )
            ] = (
                service_instance.upgrade,
                event,
                body,
                meta,
                spec,
                logger,
                kwargs,
            )
            await run_task(task_def)

    # NOTE(vsaienko): explicitly call apply() here to make sure that newly deployed environment
    # and environment after upgrade/update are identical.
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

    await run_task(task_def)

    return {"lastStatus": f"{event}d"}


@kopf.on.delete(*kube.OpenStackDeployment.kopf_on_args)
async def delete(name, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    # TODO(pas-ha) remove secrets and so on?
    LOG.info(f"deleting {name}")
