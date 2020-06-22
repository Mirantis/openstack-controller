import copy

import kopf
import pykube

from openstack_controller import kube
from openstack_controller import settings  # noqa
from openstack_controller import utils

LOG = utils.get_logger(__name__)


def update_status(owner, name, namespace, status):
    try:
        osdpl = kube.find_osdpl(owner, namespace=namespace)
    except pykube.ObjectDoesNotExist:
        LOG.warning(
            f"Failed to find OpenStackDeployment {owner} "
            f"in namespace {namespace}, skipping status update."
        )
        return
    # Set 'Unknown' state on create event when status is empty
    child_status = (
        {
            name: all(
                s["success"] is True
                for n, s in status["releaseStatuses"].items()
            )
        }
        if status
        else {name: "Unknown"}
    )
    status_patch = {"children": child_status}
    new_children_status = copy.deepcopy(
        osdpl.obj["status"].get("children", {})
    )
    new_children_status.update(child_status)
    status_patch["deployed"] = all(
        s is True for c, s in new_children_status.items()
    )
    osdpl.patch({"status": status_patch})
    LOG.info(f"Updated {name} status in {owner}")


@kopf.on.field("lcm.mirantis.com", "v1alpha1", "helmbundles", field="status")
@kopf.on.create("lcm.mirantis.com", "v1alpha1", "helmbundles")
async def helmbundle_status(body, meta, name, namespace, status, **kwargs):
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
            f"for {body['kind']} {namespace}/{name}! Ignoring."
        )
        return
    update_status(owners[0], name, namespace, status)
