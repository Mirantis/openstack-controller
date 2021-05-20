import asyncio

import kopf

from openstack_controller import cache
from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import layers
from openstack_controller import secrets
from openstack_controller import services
from openstack_controller import settings  # noqa
from openstack_controller import version
from openstack_controller import utils


LOG = utils.get_logger(__name__)


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
    """Run OpenStack controller tasks

    Runs tasks passed as `task_def` with implementing the following logic:

    * In case of permanent error retry all the tasks that finished with
      TemporaryError and fail permanently.

    * In case of unknown error retry the task as we and kopf treat error as
      environment issue which is self-recoverable. Do retries by our own
      to avoid dead locks between dependent tasks.

    :param task_def: Dictionary with the task definitions.
    :raises: kopf.PermanentError when permanent error occur.
    """

    permanent_exception = None

    while task_def:
        # NOTE(e0ne): we can switch to asyncio.as_completed to run tasks
        # faster if needed.
        done, _ = await asyncio.wait(task_def.keys())
        for task in done:
            coro, event, body, meta, spec, logger, kwargs = task_def.pop(task)
            if task.exception():
                if isinstance(task.exception(), kopf.PermanentError):
                    LOG.error(f"Failed to apply {coro} permanently.")
                    LOG.error(task.print_stack())
                    permanent_exception = kopf.PermanentError(
                        "Permanent error occured."
                    )
                else:
                    LOG.warning(
                        f"Got retriable exception when applying {coro}, retrying..."
                    )
                    LOG.warning(task.print_stack())
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

    if permanent_exception:
        raise permanent_exception


def discover_images(mspec, logger):
    cache_images = set(layers.render_cache_images() or [])
    images = {}
    for name, url in layers.render_artifacts(mspec).items():
        images.setdefault(url, []).append(name)
    return {
        names[0].replace("_", "-"): url
        for url, names in images.items()
        if set(names) & cache_images
    }


# on.field to force storing that field to be reacting on its changes
@kopf.on.field(*kube.OpenStackDeployment.kopf_on_args, field="status.children")
@kopf.on.field(*kube.OpenStackDeployment.kopf_on_args, field="status.watched")
@kopf.on.resume(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
@utils.collect_handler_metrics
async def handle(body, meta, spec, logger, event, **kwargs):
    # TODO(pas-ha) "cause" is deprecated, replace with "reason"
    event = kwargs["cause"].event
    # TODO(pas-ha) remove all this kwargs[*] nonsense, accept explicit args,
    # pass further only those that are really needed
    # actual **kwargs form is for forward-compat with kopf itself
    namespace = meta["namespace"]
    LOG.info(f"Got osdpl event {event}")
    LOG.info(f"Changes are: {kwargs['diff']}")

    kwargs["patch"].setdefault("status", {})
    kwargs["patch"]["status"]["version"] = version.release_string
    kwargs["patch"]["status"]["fingerprint"] = layers.spec_hash(body["spec"])

    # update overall deployed status based on children satuses
    children = kwargs["status"].get("children", {})
    kwargs["patch"]["status"]["deployed"] = (
        all([c is True for c in children.values()]) if children else False
    )
    LOG.debug(f"Updated status for osdpl {kwargs['name']}")

    if spec.get("draft"):
        LOG.info("OpenStack deployment is in draft mode, skipping handling...")
        return {"lastStatus": f"{event} drafted"}

    secrets.OpenStackAdminSecret(namespace).ensure()

    mspec = layers.merge_spec(body["spec"], logger)
    images = discover_images(mspec, logger)
    if images != await cache.images(meta["namespace"]):
        await cache.restart(images, body, mspec)
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
@utils.collect_handler_metrics
async def delete(name, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    # TODO(pas-ha) remove secrets and so on?
    LOG.info(f"deleting {name}")

    redis_failover = kube.find(
        kube.RedisFailover,
        "openstack-redis",
        settings.OSCTL_REDIS_NAMESPACE,
        silent=True,
    )
    if redis_failover:
        redis_failover.delete()
