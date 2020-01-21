import asyncio
from dataclasses import dataclass
from typing import List
import functools

import kopf
from mcp_k8s_lib import utils
import pykube
from typing import Dict

from . import settings

LOG = utils.get_logger(__name__)


def login():
    config = pykube.KubeConfig.from_env()
    client = pykube.HTTPClient(config)
    LOG.info(f"Created k8s api client from context {config.current_context}")
    return client


api = login()


class OpenStackDeployment(pykube.objects.NamespacedAPIObject):
    version = "lcm.mirantis.com/v1alpha1"
    kind = "OpenStackDeployment"
    endpoint = "openstackdeployments"
    kopf_on_args = *version.split("/"), endpoint


@dataclass
class HelmBundleExt:
    chart: str
    manifest: str
    images: List[str]


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
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY,
    ):
        diff = {"images": {"tags": {}}, "manifests": {}}
        for image in self.helmbundle_ext.images:
            diff["images"]["tags"][image] = self.service.get_image(
                image, self.helmbundle_ext.chart, version
            )
        diff["manifests"][self.helmbundle_ext.manifest] = True
        i = 1
        while True:
            self.service.set_release_values(diff)
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
        timeout=settings.OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY,
    ):
        await asyncio.wait_for(
            self._enable(
                version, wait_completion=wait_completion, delay=delay
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
            await self.service.set_release_values(diff)
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
        version,
        wait_completion=False,
        timeout=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT,
        delay=settings.OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY,
    ):
        await asyncio.wait_for(
            self._disable(
                version, wait_completion=wait_completion, delay=delay
            ),
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


class Deployment(pykube.Deployment, HelmBundleMixin):
    @property
    def ready(self):
        return (
            self.obj["status"]["observedGeneration"]
            >= self.obj["metadata"]["generation"]
            and self.obj["status"].get("updatedReplicas") == self.replicas
            and self.obj["status"].get("readyReplicas") == self.replicas
        )


def resource(data):
    return pykube.object_factory(api, data["apiVersion"], data["kind"])(
        api, data
    )


def dummy(klass, name, namespace=None):
    meta = {"name": name}
    if namespace:
        meta["namespace"] = namespace
    return klass(api, {"metadata": meta})


def find(klass, name, namespace=None):
    return klass.objects(api).filter(namespace=namespace).get(name=name)


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


def wait_for_secret(namespace, name):
    wait_for_resource(pykube.Secret, name, namespace)


def save_secret_data(namespace: str, name: str, data: Dict[str, str]):
    secret = {"metadata": {"name": name, "namespace": namespace}, "data": data}
    try:
        find(pykube.Secret, name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        pykube.Secret(api, secret).create()
    else:
        pykube.Secret(api, secret).update()


find_osdpl = functools.partial(find, OpenStackDeployment)
