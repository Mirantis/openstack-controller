import glob
import logging
import time
import yaml

from openstack_controller import kube
from openstack_controller import utils

logging.basicConfig()
LOG = utils.get_logger(__name__)


CONFIG_DIRECTORY = "/etc/resources"
WAIT_FOR_RESOURCE_DELAY = 5


def _wait_for_obj(obj):
    """ Continiously wait for obj.
    """
    while not obj.exists():
        LOG.info(f"Still waiting for resource: {obj.kind}:{obj.name}")
        time.sleep(WAIT_FOR_RESOURCE_DELAY)


def main():
    for resource_file in sorted(glob.glob(f"{CONFIG_DIRECTORY}/*.yaml")):
        with open(resource_file, "r") as f:
            for document in yaml.load_all(f):
                LOG.debug(
                    f"Handling resorce document {document} from file: {resource_file}"
                )
                if "kind" not in document.keys():
                    LOG.info(f"Skipping document, doesn't have kind")
                    continue
                obj = kube.object_factory(
                    kube.api, document["apiVersion"], document["kind"]
                )(kube.api, document)
                action = (
                    document["metadata"]
                    .get("annotations", {})
                    .get(
                        "openstackdeployments.lcm.mirantis.com/shared_resource_action",
                        "create",
                    )
                )

                if action == "create":
                    if obj.exists():
                        LOG.info(f"Updating {obj.kind}:{obj.name}")
                        obj.reload()
                        obj.set_obj(document)
                        obj.update()
                    else:
                        LOG.info(f"Creating {obj.kind}:{obj.name}")
                        obj.create()
                        # NOTE(vsaienko): wait for resource is initlialized, to ensure we can use it
                        _wait_for_obj(obj)
                elif action == "wait":
                    _wait_for_obj(obj)
