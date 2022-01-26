#!/usr/bin/env python3
import asyncio

import pykube

from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import utils


LOG = utils.get_logger("remove-old-finalizer")

DEFAULT_KOPF_FINALIZER = "kopf.zalando.org/KopfFinalizerMarker"
WATCHED_KINDS = [
    "DaemonSet",
    "StatefulSet",
    "Deployment",
    "Node",
    "OpenStackDeployment",
]


async def _main():
    for kkind in WATCHED_KINDS:
        kclass = kube.get_object_by_kind(kkind)
        namespace = settings.OSCTL_OS_DEPLOYMENT_NAMESPACE
        if not issubclass(kclass, pykube.objects.NamespacedAPIObject):
            namespace = None
        for obj in kube.resource_list(
            kclass, selector=None, namespace=namespace
        ):
            if DEFAULT_KOPF_FINALIZER in obj.metadata.get("finalizers", []):
                LOG.info(
                    f"Removing default finalizer for {kclass.__name__}: {obj.metadata['name']}"
                )
                finalizers = obj.metadata["finalizers"]
                finalizers.remove(DEFAULT_KOPF_FINALIZER)
                obj.patch({"metadata": {"finalizers": finalizers}})


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())
