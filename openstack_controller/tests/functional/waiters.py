import time
import logging

from openstack_controller.tests.functional import config as conf

LOG = logging.getLogger(__name__)


def wait_for_compute_service_state(client, compute_svc, state="up"):
    service_id = compute_svc["id"]

    start_time = int(time.time())
    timeout = conf.COMPUTE_TIMEOUT
    while True:
        service = client.oc.compute.find_service(name_or_id=service_id)
        service_state = service["state"]
        if service_state == state:
            LOG.debug(
                "Current service has {} state: {}.".format(
                    service_id, service_state
                )
            )
            return
        time.sleep(conf.COMPUTE_BUILD_INTERVAL)
        timed_out = int(time.time()) - start_time
        message = "Current service {} has state: {}. Expected state: {}, after {} sec".format(
            service_id, service_state, state, timed_out
        )
        if timed_out >= timeout:
            LOG.error(message)
            raise TimeoutError(message)


def wait_for_compute_service_status(client, compute_svc, status="enabled"):
    service_id = compute_svc["id"]

    start_time = int(time.time())
    timeout = conf.COMPUTE_TIMEOUT
    while True:
        service = client.oc.compute.find_service(name_or_id=service_id)
        service_status = service["status"]
        if service_status == status:
            LOG.debug(
                "Current service has {} status: {}.".format(
                    service_id, service_status
                )
            )
            return
        time.sleep(conf.COMPUTE_BUILD_INTERVAL)
        timed_out = int(time.time()) - start_time
        message = "Current service {} has status: {}. Expected status: {}, after {} sec".format(
            service_id, service_status, status, timed_out
        )
        if timed_out >= timeout:
            LOG.error(message)
            raise TimeoutError(message)
