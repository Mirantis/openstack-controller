import asyncio

import kopf

from openstack_controller import cache
from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import layers
from openstack_controller import maintenance
from openstack_controller import secrets
from openstack_controller import services
from openstack_controller import settings  # noqa
from openstack_controller import version
from openstack_controller import utils
from openstack_controller import osdplstatus


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


def check_handling_allowed(old, new, event):
    LOG.info(f"Checking whether handling is allowed")

    new_values = (
        new.get("spec", {})
        .get("services", {})
        .get("database", {})
        .get("mariadb", {})
        .get("values", {})
    )
    new_enabled = new_values.get("manifests", {}).get(
        "job_mariadb_phy_restore", False
    )

    if new_enabled:
        if event == "create":
            raise kopf.PermanentError(
                f"Mariadb restore cannot be enabled during Openstack deployment create"
            )
        elif event == "resume":
            raise kopf.PermanentError(
                f"Resume is blocked due to Mariadb restore job enabled"
            )
        else:
            old_values = (
                old.get("spec", {})
                .get("services", {})
                .get("database", {})
                .get("mariadb", {})
                .get("values", {})
            )
            old_enabled = old_values.get("manifests", {}).get(
                "job_mariadb_phy_restore", False
            )
            if old_enabled:
                raise kopf.PermanentError(
                    f"Mariadb restore job should be disabled before doing other changes, handling is not allowed"
                )
    LOG.info("Handling is allowed")


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
        LOG.info("Sleeping ...")
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
@kopf.on.field(*kube.OpenStackDeployment.kopf_on_args, field="status.watched")
@kopf.on.resume(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
@utils.collect_handler_metrics
async def handle(body, meta, spec, logger, reason, **kwargs):
    # TODO(pas-ha) remove all this kwargs[*] nonsense, accept explicit args,
    # pass further only those that are really needed
    # actual **kwargs form is for forward-compat with kopf itself
    namespace = meta["namespace"]
    name = meta["name"]
    LOG.info(f"Got osdpl event {reason}")
    LOG.info(f"Changes are: {kwargs['diff']}")

    # TODO(vsaienko): remove legacy status
    kwargs["patch"].setdefault("status", {})
    kwargs["patch"]["status"]["version"] = version.release_string
    kwargs["patch"]["status"]["fingerprint"] = layers.spec_hash(body["spec"])
    osdplst = osdplstatus.OpenStackDeploymentStatus(name, namespace)
    osdplst.present()

    # Always create clusterworkloadlock, but set to inactive when we are not interested
    cwl = maintenance.ClusterWorkloadLock.get_resource(name)
    cwl.present()

    if not settings.OSCTL_NODE_MAINTENANCE_ENABLED:
        cwl.set_state_inactive()
    osdplst.set_osdpl_status(
        osdplstatus.APPLYING, body["spec"], kwargs["diff"], reason
    )

    if spec.get("draft"):
        LOG.info("OpenStack deployment is in draft mode, skipping handling...")
        return {"lastStatus": f"{reason} drafted"}

    check_handling_allowed(kwargs["old"], kwargs["new"], reason)

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
        for service in set(list(services_to_upgrade) + list(update)):
            osdplst.set_service_state(service, osdplstatus.WAITING)
        for service in services_to_upgrade:
            task_def = {}
            service_instance = services.registry[service](
                body, logger, osdplst
            )
            task_def[
                asyncio.create_task(
                    service_instance.upgrade(
                        event=reason,
                        body=body,
                        meta=meta,
                        spec=spec,
                        logger=logger,
                        **kwargs,
                    )
                )
            ] = (
                service_instance.upgrade,
                reason,
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
        service_instance = services.registry[service](body, logger, osdplst)
        task_def[
            asyncio.create_task(
                service_instance.apply(
                    event=reason,
                    body=body,
                    meta=meta,
                    spec=spec,
                    logger=logger,
                    **kwargs,
                )
            )
        ] = (service_instance.apply, reason, body, meta, spec, logger, kwargs)

    if delete:
        LOG.info(f"deleting children {' '.join(delete)}")
    for service in delete:
        service_instance = services.registry[service](body, logger, osdplst)
        task_def[
            asyncio.create_task(
                service_instance.delete(
                    body=body, meta=meta, spec=spec, logger=logger, **kwargs
                )
            )
        ] = (service_instance.delete, reason, body, meta, spec, logger, kwargs)

    await run_task(task_def)

    # If we got here, we installed all releases successfully.
    # TODO(vsaienko): remove legacy status
    kwargs["patch"]["status"]["deployed"] = True
    osdplst.set_osdpl_status(
        osdplstatus.APPLIED, body["spec"], kwargs["diff"], reason
    )

    return {"lastStatus": f"{reason}d"}


@kopf.on.delete(*kube.OpenStackDeployment.kopf_on_args)
@utils.collect_handler_metrics
async def delete(name, meta, body, spec, logger, reason, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    # TODO(pas-ha) remove secrets and so on?
    LOG.info(f"Deleting {name}")
    namespace = meta["namespace"]
    osdplst = osdplstatus.OpenStackDeploymentStatus(name, namespace)
    delete_services = layers.services(spec, logger, **kwargs)[0]
    for service in delete_services:
        LOG.info(f"Deleting {service} service")
        task_def = {}
        service_instance = services.registry[service](body, logger, osdplst)
        task_def[
            asyncio.create_task(
                service_instance.delete(
                    body=body, meta=meta, spec=spec, logger=logger, **kwargs
                )
            )
        ] = (service_instance.delete, reason, body, meta, spec, logger, kwargs)
        await run_task(task_def)
    # TODO(dbiletskiy) delete osdpl status
    kube.ClusterWorkloadLock.get_resource(name).absent()
