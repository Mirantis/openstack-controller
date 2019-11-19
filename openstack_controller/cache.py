import kopf
import pykube

from . import kube
from . import layers

from mcp_k8s_lib import utils


LOG = utils.get_logger(__name__)


async def _get(namespace, i):
    try:
        return kube.find(pykube.DaemonSet, f"{kube.CACHE_NAME}-{i}", namespace)
    except pykube.exceptions.PyKubeError:
        return None


async def _list(namespace):
    return kube.resource_list(
        pykube.DaemonSet, {"k8s-app__in": {"image-precaching"}}, namespace
    )


async def images(namespace):
    images = {}
    daemons = await _list(namespace)
    for ds in daemons:
        images.update(
            {
                i["name"].replace("image-precaching-", ""): i["image"]
                for i in ds.obj["spec"]["template"]["spec"]["containers"]
            }
        )
    LOG.debug(
        f"Checking cached images. Daemons inspected: {len(daemons)}, images found: {len(images)}"
    )
    return images


async def restart(images, osdpl):
    namespace = osdpl["metadata"]["namespace"]
    log_showed = False
    for ds in await _list(namespace):
        ds.delete()
        if not log_showed:
            LOG.info("Stopping cache ...")
            log_showed = True
        # TODO(avolkov): wait for delete completion
    image_groups = []
    if not images:
        LOG.info("No images to cache. Skip caching")
    else:
        image_list = list(images.items())
        # NOTE(avolkov): images_per_daemon determines how many
        #   daemonsets start depending on total number of images we
        #   need to cache.
        images_per_daemon = 50
        image_groups = [
            dict(image_list[i : i + images_per_daemon])
            for i in range(0, len(image_list), images_per_daemon)
        ]
        LOG.info(
            f"Starting cache (images: {len(images)}, instances: {len(image_groups)}) ..."
        )
        for i in range(len(image_groups)):
            cache = layers.render_cache_template(
                osdpl, f"{kube.CACHE_NAME}-{i}", image_groups[i]
            )
            kopf.adopt(cache, osdpl)
            kube.resource(cache).create()
    return len(image_groups)


async def wait_ready(namespace):
    for ds in await _list(namespace):
        kube.wait_for_daemonset_ready(ds.obj["metadata"]["name"], namespace)
