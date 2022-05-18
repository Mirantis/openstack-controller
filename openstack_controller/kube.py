import asyncio
from dataclasses import dataclass
import inspect
import json
import sys
from typing import List
import functools

import kopf
import pykube
from typing import Dict

from . import constants as const
from . import settings
from . import utils

LOG = utils.get_logger(__name__)


def login():
    config = pykube.KubeConfig.from_env()
    client = pykube.HTTPClient(
        config=config, timeout=settings.OSCTL_PYKUBE_HTTP_REQUEST_TIMEOUT
    )
    LOG.info(f"Created k8s api client from context {config.current_context}")
    return client


api = login()


def get_kubernetes_objects():
    """Return all classes that are subclass of pykube.objects.APIObject.

    The following order is used:
    1. openstack_controller.pykube classes
    2. pykube.objects classes

    """

    def _get_kubernetes_objects(module):
        k_objects = {}
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, pykube.objects.APIObject)
                and getattr(obj, "kind", None)
            ):
                k_objects[(obj.version, obj.kind)] = obj
        return k_objects

    objects = _get_kubernetes_objects(pykube.objects)
    objects.update(_get_kubernetes_objects(sys.modules[__name__]))
    return objects


KUBE_OBJECTS = get_kubernetes_objects()


def get_object_by_kind(kind):
    for item, kube_class in get_kubernetes_objects().items():
        if kind == item[1]:
            return kube_class


def object_factory(api, api_version, kind):
    """Dynamically builds kubernetes objects python class.

    1. Objects from openstack_operator.pykube.KUBE_OBJECTS
    2. Objects from pykube.objects
    3. Generic kubernetes object
    """
    resource = KUBE_OBJECTS.get(
        (api_version, kind), pykube.object_factory(api, api_version, kind)
    )
    return resource


class OpenStackDeployment(pykube.objects.NamespacedAPIObject):
    version = "lcm.mirantis.com/v1alpha1"
    kind = "OpenStackDeployment"
    endpoint = "openstackdeployments"
    kopf_on_args = *version.split("/"), endpoint


class OpenStackDeploymentSecret(pykube.objects.NamespacedAPIObject):
    version = "lcm.mirantis.com/v1alpha1"
    kind = "OpenStackDeploymentSecret"
    endpoint = "openstackdeploymentsecrets"
    kopf_on_args = *version.split("/"), endpoint

    def __init__(self, name, namespace, *args, **kwargs):
        self.dummy = {
            "apiVersion": self.version,
            "kind": self.kind,
            "metadata": {"name": name, "namespace": namespace},
            "spec": {},
            "status": {},
        }
        return super().__init__(api, self.dummy)


class HelmBundle(pykube.objects.NamespacedAPIObject):
    version = "lcm.mirantis.com/v1alpha1"
    kind = "HelmBundle"
    endpoint = "helmbundles"
    kopf_on_args = *version.split("/"), endpoint


@dataclass
class HelmBundleExt:
    chart: str
    manifest: str
    images: List[str]
    # List of jsonpath-ng expressions, describes values in release
    # that modify immutable fields.
    hash_fields: List[str]


class HelmBundleMixin:

    __helmbundle_ext = {}
    immutable = False

    @property
    def service(self):
        return self.__service

    @service.setter
    def service(self, service):
        self.__service = service

    @property
    def helmbundle_ext(self) -> HelmBundleExt:
        return self.__helmbundle_ext

    @helmbundle_ext.setter
    def helmbundle_ext(self, helmbundle_ext: HelmBundleExt):
        self.__helmbundle_ext = helmbundle_ext

    async def _enable(
        self,
        version,
        wait_completion=False,
        extra_values=None,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY,
    ):
        diff = {"images": {"tags": {}}, "manifests": {}}
        for image in self.helmbundle_ext.images:
            diff["images"]["tags"][image] = self.service.get_image(
                image, self.helmbundle_ext.chart, version
            )
        diff["manifests"][self.helmbundle_ext.manifest] = True
        if extra_values is not None:
            diff.update(extra_values)

        i = 1
        while True:
            await self.service.set_release_values(
                self.helmbundle_ext.chart, diff
            )
            if not wait_completion:
                return
            if self.exists():
                self.reload()
                applied_images = []
                for image in self.helmbundle_ext.images:
                    if self.image_applied(
                        self.service.get_image(
                            image, self.helmbundle_ext.chart, version
                        )
                    ):
                        applied_images.append(image)
                if len(applied_images) > 0 and self.ready:
                    return
                LOG.info(
                    f"The images are not updated yet for {self.kind} {self.name}."
                )
            LOG.info(
                f"The {self.kind} {self.name} is not ready. Waiting, attempt: {i}"
            )
            i += 1
            await asyncio.sleep(delay)

    async def enable(
        self,
        version,
        wait_completion=False,
        extra_values=None,
        timeout=settings.OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY,
    ):
        await asyncio.wait_for(
            self._enable(
                version,
                wait_completion=wait_completion,
                extra_values=extra_values,
                delay=delay,
            ),
            timeout=timeout,
        )

    async def _disable(
        self,
        wait_completion=False,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY,
    ):
        diff = {"images": {"tags": {}}, "manifests": {}}
        diff["manifests"][self.helmbundle_ext.manifest] = False
        i = 1
        while True:
            await self.service.set_release_values(
                self.helmbundle_ext.chart, diff
            )
            if not wait_completion:
                return
            if not self.exists():
                return
            LOG.info(
                f"The object {self.kind} {self.name} still exists, retrying {i}"
            )
            await asyncio.sleep(delay)
            i += 1

    async def disable(
        self,
        wait_completion=False,
        timeout=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY,
    ):
        await asyncio.wait_for(
            self._disable(wait_completion=wait_completion, delay=delay),
            timeout=timeout,
        )

    async def _purge(
        self,
        timeout=settings.OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY,
    ):
        i = 1
        while True:
            if not self.exists():
                LOG.info(f"Object {self.kind}: {self.name} is not present.")
                return
            self.delete(propagation_policy="Background")
            LOG.info(
                f"Retrying {i} removing {self.kind}: {self.name} in {delay}s"
            )
            i += 1
            await asyncio.sleep(delay)

    async def purge(
        self,
        timeout=settings.OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY,
    ):
        await asyncio.wait_for(self._purge(delay=delay), timeout=timeout)

    def image_applied(self, value):
        """Ensure image is applied to at least one of containers"""
        self.reload()
        for container in self.obj["spec"]["template"]["spec"]["containers"]:
            if container["image"] == value:
                LOG.info(
                    f"Found image in container {container['name']} for {self.kind}: {self.name}"
                )
                return True


class Secret(pykube.Secret, HelmBundleMixin):
    pass


class Service(pykube.Service, HelmBundleMixin):
    pass


class StatefulSet(pykube.StatefulSet, HelmBundleMixin):
    @property
    def ready(self):
        return (
            self.obj["status"]["observedGeneration"]
            >= self.obj["metadata"]["generation"]
            and self.obj["status"].get("updatedReplicas") == self.replicas
            and self.obj["status"].get("readyReplicas") == self.replicas
        )


class Ingress(pykube.objects.NamespacedAPIObject, HelmBundleMixin):
    version = "extensions/v1beta1"
    endpoint = "ingresses"
    kind = "Ingress"


class Job(pykube.Job, HelmBundleMixin):

    immutable = True

    @property
    def ready(self):
        self.reload()
        conditions = self.obj.get("status", {}).get("conditions", [])
        # TODO(vsaienko): there is no official documentation that describes when job is considered complete.
        # revisit this place in future.
        completed = [
            c["status"] == "True"
            for c in conditions
            if c["type"] in ["Ready", "Complete"]
        ]
        if completed and all(completed):
            LOG.info(
                f"All conditions for the {self.kind} {self.name} completed."
            )
            return True
        LOG.info(
            f"Some conditions {conditions} for the {self.kind} {self.name} not completed."
        )
        return False

    def _prepare_for_rerun(self):
        # cleanup the object of runtime stuff
        self.obj.pop("status", None)
        self.obj["metadata"].pop("creationTimestamp", None)
        self.obj["metadata"].pop("resourceVersion", None)
        self.obj["metadata"].pop("selfLink", None)
        self.obj["metadata"].pop("uid", None)
        self.obj["metadata"]["labels"].pop("controller-uid", None)
        self.obj["spec"]["template"]["metadata"].pop("creationTimestamp", None)
        self.obj["spec"]["template"]["metadata"]["labels"].pop(
            "controller-uid", None
        )
        self.obj["spec"].pop("selector", None)

    async def rerun(self):
        self.delete(propagation_policy="Background")
        if not await wait_for_deleted(self):
            LOG.warning("Failed to delete job %s", self.name)
            return
        self._prepare_for_rerun()
        self.create()
        LOG.info("New job created: %s", self.name)


class CronJob(pykube.CronJob, HelmBundleMixin):
    async def _suspend(
        self,
        wait_completion=False,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY,
    ):
        diff = {"conf": {"cronjob": {"suspend": True}}}
        i = 1
        while True:
            self.reload()
            await self.service.set_release_values(
                self.helmbundle_ext.chart, diff
            )
            if not wait_completion:
                return
            check_apply = self.obj["spec"].get("suspend", None)
            if check_apply:
                return
            LOG.info(
                f"The object {self.kind} {self.name} still not suspended, retrying {i}"
            )
            await asyncio.sleep(delay)
            i += 1

    async def suspend(
        self,
        wait_completion=False,
        timeout=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY,
    ):
        await asyncio.wait_for(
            self._suspend(wait_completion=wait_completion, delay=delay),
            timeout=timeout,
        )


class Deployment(pykube.Deployment, HelmBundleMixin):
    @property
    def ready(self):
        return (
            self.obj["status"]["observedGeneration"]
            >= self.obj["metadata"]["generation"]
            and self.obj["status"].get("updatedReplicas") == self.replicas
            and self.obj["status"].get("readyReplicas") == self.replicas
        )

    async def wait_for_replicas(self, count, times=60, seconds=10):
        for i in range(times):
            self.reload()
            # NOTE(vsaienko): the key doesn't exist when have 0 replicas
            if self.obj["status"].get("readyReplicas", 0) == count:
                return True
            await asyncio.sleep(seconds)
        return False


class DaemonSet(pykube.DaemonSet, HelmBundleMixin):
    @property
    def ready(self):
        return self.obj["status"]["observedGeneration"] >= self.obj[
            "metadata"
        ]["generation"] and self.obj["status"].get(
            "updatedNumberScheduled"
        ) == self.obj[
            "status"
        ].get(
            "numberReady"
        )


class Pod(pykube.Pod):

    # NOTE(vsaienko): override delete method unless client accepts grace_period parameter
    def delete(
        self, propagation_policy: str = None, grace_period_seconds=None
    ):
        """
        Delete the Kubernetes resource by calling the API.
        The parameter propagation_policy defines whether to cascade the delete. It can be "Foreground", "Background" or "Orphan".
        See https://kubernetes.io/docs/concepts/workloads/controllers/garbage-collection/#setting-the-cascading-deletion-policy
        """
        options = {}
        if propagation_policy:
            options["propagationPolicy"] = propagation_policy
        if grace_period_seconds is not None:
            options["gracePeriodSeconds"] = grace_period_seconds
        r = self.api.delete(**self.api_kwargs(data=json.dumps(options)))
        if r.status_code != 404:
            self.api.raise_for_status(r)

    @property
    def job_child(self):
        for owner in self.metadata["ownerReferences"]:
            if owner["kind"] == "Job":
                return True
        return False


class Node(pykube.Node):
    @property
    def ready(self):
        """
        Return whether the given pykube Node has "Ready" status
        """
        self.reload()
        for condition in self.obj.get("status", {}).get("conditions", []):
            if condition["type"] == "Ready" and condition["status"] == "True":
                return True
        return False

    def get_pods(self, namespace=None):
        pods = Pod.objects(api).filter(namespace=namespace)
        pods = [
            pod for pod in pods if pod.obj["spec"].get("nodeName") == self.name
        ]
        return pods

    def remove_pods(self, namespace=None):
        pods = self.get_pods(namespace=namespace)
        for pod in pods:
            LOG.debug(f"Removing pod: {pod.name} from node: {self.name}")
            pod.delete(propagation_policy="Background", grace_period_seconds=0)

    def has_role(self, role: const.NodeRole) -> bool:
        if role not in const.NodeRole:
            LOG.warning(f"Unknown node role {role.value}, ignoring...")
            return False
        for k, v in settings.OSCTL_OPENSTACK_NODE_LABELS[role].items():
            if self.labels.get(k) == v:
                return True
        return False


class RedisFailover(pykube.objects.NamespacedAPIObject):
    version = "databases.spotahome.com/v1"
    kind = "RedisFailover"
    endpoint = "redisfailovers"


def resource(data):
    return object_factory(api, data["apiVersion"], data["kind"])(api, data)


def dummy(klass, name, namespace=None):
    meta = {"name": name}
    if namespace:
        meta["namespace"] = namespace
    return klass(api, {"metadata": meta})


def find(klass, name, namespace=None, silent=False, cluster=False):
    try:
        if cluster:
            return klass.objects(api).get(name=name)
        return klass.objects(api).filter(namespace=namespace).get(name=name)
    except pykube.exceptions.ObjectDoesNotExist:
        if not silent:
            raise


def resource_list(klass, selector, namespace=None):
    return klass.objects(api).filter(namespace=namespace, selector=selector)


def wait_for_resource(klass, name, namespace=None, delay=60):
    try:
        find(klass, name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        raise kopf.TemporaryError(
            f"The object: {klass.kind} with name '{name}' is not found yet.",
            delay=delay,
        )
    except:
        raise kopf.TemporaryError(
            f"Unknown error occured while getting object: {klass.kind}.",
            delay=delay,
        )


def wait_for_daemonset_ready(name, namespace=None, delay=60):
    try:
        ds = find(pykube.DaemonSet, name, namespace)
        if not int(ds.obj["status"]["desiredNumberScheduled"]):
            raise ValueError("Not scheduled yet")
        if int(ds.obj["status"]["desiredNumberScheduled"]) != int(
            ds.obj["status"]["numberReady"]
        ):
            raise ValueError("Not ready yet")

    except pykube.exceptions.ObjectDoesNotExist:
        raise kopf.TemporaryError(
            f"The DaemonSet is not found yet.", delay=delay
        )
    except Exception as e:
        raise kopf.TemporaryError(
            f"An error occured while getting DaemonSet {name} ({e}).",
            delay=delay,
        )


def wait_for_secret(namespace, name):
    wait_for_resource(pykube.Secret, name, namespace)


def save_secret_data(
    namespace: str, name: str, data: Dict[str, str], labels=None
):
    secret = {"metadata": {"name": name, "namespace": namespace}, "data": data}
    if labels is not None:
        secret["metadata"]["labels"] = labels

    try:
        find(pykube.Secret, name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        pykube.Secret(api, secret).create()
    else:
        pykube.Secret(api, secret).update()


async def wait_for_deleted(
    obj,
    times=settings.OSCTL_RESOURCE_DELETED_WAIT_RETRIES,
    seconds=settings.OSCTL_RESOURCE_DELETED_WAIT_TIMEOUT,
):
    for i in range(times):
        if not obj.exists():
            return True
        await asyncio.sleep(seconds)
    return False


def get_osdpl(namespace=settings.OSCTL_OS_DEPLOYMENT_NAMESPACE):
    LOG.debug("Getting osdpl object")
    osdpl = list(OpenStackDeployment.objects(api).filter(namespace=namespace))
    if len(osdpl) != 1:
        LOG.warning(
            f"Could not find unique OpenStackDeployment resource "
            f"in namespace {namespace}, skipping health report processing."
        )
        return
    return osdpl[0]


find_osdpl = functools.partial(find, OpenStackDeployment)
