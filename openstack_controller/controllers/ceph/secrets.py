import json
import kopf
import hashlib

from openstack_controller import ceph_api
from openstack_controller import health
from openstack_controller import settings  # noqa
from openstack_controller import utils

LOG = utils.get_logger(__name__)


@kopf.on.resume(
    "",
    "v1",
    "secrets",
)
@kopf.on.update(
    "",
    "v1",
    "secrets",
)
async def handle_ceph_shared_secret(
    body,
    meta,
    name,
    status,
    logger,
    diff,
    **kwargs,
):

    if name != ceph_api.OPENSTACK_KEYS_SECRET:
        return
    LOG.debug(f"Handling secret create/update {name}")
    osdpl = health.get_osdpl(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)

    hasher = hashlib.sha256()
    hasher.update(json.dumps(body["data"], sort_keys=True).encode())
    secret_hash = hasher.hexdigest()

    osdpl.patch(
        {"status": {"watched": {"ceph": {"secret": {"hash": secret_hash}}}}}
    )
