import datetime
import kopf
import time

from openstack_controller import settings
from openstack_controller import utils


LOG = utils.get_logger(__name__)


@kopf.on.probe(id="now")
def get_current_timestamp(**kwargs):
    return datetime.datetime.utcnow().isoformat()


@kopf.on.probe(id="delay")
def check_heartbeat(**kwargs):
    delay = None
    if settings.OSCTL_HEARTBEAT_INTERVAL:
        delay = time.time() - settings.HEARTBEAT
        LOG.debug(f"Current heartbeat delay {delay}")
        if delay > settings.OSCTL_HEARTBEAT_MAX_DELAY:
            raise ValueError("Heartbeat delay is too large")
    return delay
