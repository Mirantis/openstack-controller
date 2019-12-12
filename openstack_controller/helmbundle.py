import copy

import kopf
from mcp_k8s_lib import utils
import pykube

from . import kube

LOG = utils.get_logger(__name__)


async def update_status(owner, meta, status):
    try:
        osdpl = kube.find_osdpl(owner, namespace=meta["namespace"])
    except pykube.ObjectDoesNotExist:
        LOG.warning(
            f"Failed to find OpenStackDeployment {owner} "
            f"in namespace {meta['namespace']}, skipping status update."
        )
        return
    child_status = {
        meta["name"]: all(
            s["success"] is True for n, s in status["releaseStatuses"].items()
        )
    }
    status_patch = {"children": child_status}
    new_children_status = copy.deepcopy(
        osdpl.obj["status"].get("children", {})
    )
    new_children_status.update(child_status)
    status_patch["deployed"] = all(
        s is True for c, s in new_children_status.items()
    )
    osdpl.patch({"status": status_patch})
    LOG.info(f"Updated {meta['name']} status in {owner}")


@kopf.on.field("lcm.mirantis.com", "v1alpha1", "helmbundles", field="status")
async def status(body, meta, status, logger, diff, **kwargs):
    namespace = meta["namespace"]
    owners = [
        o["name"]
        for o in meta.get("ownerReferences", [])
        if o["kind"] == kube.OpenStackDeployment.kind
        and o["apiVersion"] == kube.OpenStackDeployment.version
    ]
    if not owners:
        LOG.info("Not managed by openstack-controller, ignoring")
        return
    elif len(owners) > 1:
        LOG.error(
            f"Several owners of kind OpenStackDeployment "
            f"for {body['kind']} {namespace}/{meta['name']}! Ignoring."
        )
        return
    await update_status(owners[0], meta, status)
