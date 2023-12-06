import time
import logging

from openstack_controller.tests.functional import config as conf
from openstack_controller import openstack_utils

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


def wait_for_volume_service_status(volume_svc, status="enabled"):
    start_time = int(time.time())
    timeout = conf.VOLUME_TIMEOUT
    while True:
        client = openstack_utils.OpenStackClientManager()
        service = client.volume_get_services(
            host=volume_svc["host"], binary=volume_svc["binary"]
        )
        service_status = service[0]["status"]
        if service_status == status:
            LOG.debug(
                "Current service {} has status: {}.".format(
                    volume_svc["binary"], service_status
                )
            )
            return
        time.sleep(conf.VOLUME_BUILD_INTERVAL)
        timed_out = int(time.time()) - start_time
        message = "Current service {} has status: {}. Expected status: {}, after {} sec".format(
            volume_svc["binary"], service_status, status, timed_out
        )
        if timed_out >= timeout:
            LOG.error(message)
            raise TimeoutError(message)


def wait_for_server_status(openstack_client, server, status):
    start_time = int(time.time())
    timeout = conf.SERVER_TIMEOUT
    while True:
        server = openstack_client.oc.get_server(server.id)
        if server.status.upper() == status.upper():
            LOG.debug(f"Server {server.id} has status: {server.status}.")
            return
        time.sleep(conf.SERVER_READY_INTERVAL)
        timed_out = int(time.time()) - start_time
        if timed_out >= timeout:
            message = (
                f"Server {server.id} failed to reach {status} "
                f"status within the required time {timeout}"
            )
            LOG.error(message)
            raise TimeoutError(message)


def wait_for_port_status(openstack_client, port, status):
    start_time = int(time.time())
    timeout = conf.SERVER_TIMEOUT
    while True:
        port = openstack_client.oc.network.get_port(port.id)
        if port.status.upper() == status.upper():
            LOG.debug(f"Port {port.id} has status: {port.status}.")
            return
        time.sleep(conf.SERVER_READY_INTERVAL)
        timed_out = int(time.time()) - start_time
        if timed_out >= timeout:
            message = (
                f"Port {port.id} failed to reach {status} "
                f"status within the required time {timeout}"
            )
            LOG.error(message)
            raise TimeoutError(message)
