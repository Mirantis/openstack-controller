import asyncio
from dataclasses import dataclass
import logging

from openstack_controller import constants
from openstack_controller import kube
from openstack_controller import settings

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeploymentStatusCondition:
    status: str
    type: str
    reason: str
    message: str
    lastUpdateTime: str
    lastTransitionTime: str


@dataclass(frozen=True)
class StatefulSetStatus:
    observedGeneration: int
    replicas: int
    currentRevision: str
    updateRevision: str  # optional?
    collisionCount: int
    readyReplicas: int = 0
    updatedReplicas: int = 0
    currentReplicas: int = 0


@dataclass(frozen=True)
class DaemonSetStatus:
    currentNumberScheduled: int
    numberMisscheduled: int
    desiredNumberScheduled: int
    numberReady: int
    observedGeneration: int
    numberAvailable: int = 0
    numberUnavailable: int = 0
    updatedNumberScheduled: int = 0


def ident(meta):
    name = meta["name"]
    application = meta.get("labels", {}).get("application", name)
    component = meta.get("labels", {}).get("component", name)

    # single out prometheus-exported Deployments
    if application.startswith("prometheus") and component == "exporter":
        application = "prometheus-exporter"
        # examples:
        # name=openstack-barbican-rabbitmq-rabbitmq-exporter
        # name=openstack-memcached-memcached-exporter
        # name=prometheus-mysql-exporter
        prefix, component, *parts = name.split("-")
        if parts[0] == "rabbitmq" and component != "rabbitmq":
            component += "-rabbitmq"
    # single out rabbitmq StatefulSets
    # examples:
    # name=openstack-nova-rabbitmq-rabbitmq
    # name=openstack-rabbitmq-rabbitmq
    elif application == "rabbitmq" and component == "server":
        prefix, service, *parts = name.split("-")
        if service != "rabbitmq":
            application = service
            component = "rabbitmq"
    else:
        # For other cases pick component name from resource name to allow multiple
        # resources per same component/application.
        # Remove redundant {applicaion}- part
        short_component_name = name.split(f"{application}-", maxsplit=1)[-1]
        if short_component_name:
            component = short_component_name

    return application, component


def set_application_health(
    osdpl, application, component, namespace, health, observed_generation
):
    patch = {
        application: {
            component: {"status": health, "generation": observed_generation,}
            if health is not None
            else None
        }
    }
    osdpl.patch({"status": {"health": patch}})


def is_application_ready(application, osdpl):
    osdpl = kube.OpenStackDeployment(kube.api, osdpl.obj)
    osdpl.reload()

    app_status = osdpl.obj.get("status", {}).get("health", {}).get(application)
    if not app_status:
        LOG.info(
            f"Application: {application} is not present in .status.health."
        )
        return False
    elif all(
        [
            component_health["status"] == constants.OK
            for component_health in app_status.values()
        ]
    ):
        LOG.info(f"All components for application: {application} are healty.")
        return True

    not_ready = [
        component
        for component, health in app_status.items()
        if health["status"] != "Ready"
    ]
    LOG.info(
        f"Some components for application: {application} not ready: {not_ready}"
    )
    return False


async def _wait_application_ready(
    application, osdpl, delay=settings.OSCTL_WAIT_APPLICATION_READY_DELAY
):
    i = 1
    while not is_application_ready(application, osdpl):
        LOG.info(f"Checking application {application} health, attempt: {i}")
        i += 1
        await asyncio.sleep(delay)


async def wait_application_ready(
    application,
    osdpl,
    timeout=settings.OSCTL_WAIT_APPLICATION_READY_TIMEOUT,
    delay=settings.OSCTL_WAIT_APPLICATION_READY_DELAY,
):
    LOG.info(f"Waiting for application becomes ready for {timeout}s")
    await asyncio.wait_for(
        _wait_application_ready(application, osdpl, delay=delay),
        timeout=timeout,
    )
