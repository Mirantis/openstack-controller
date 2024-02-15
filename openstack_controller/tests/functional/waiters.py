import time
import logging

import openstack

from openstack_controller.tests.functional import config

LOG = logging.getLogger(__name__)
CONF = config.Config()


def wait_for_service_status_state(
    fetch_function, svc, expected_status, timeout, interval
):
    start_time = int(time.time())
    while True:
        current_service_status = fetch_function(svc)
        if current_service_status == expected_status:
            LOG.debug(f"Current service status is {current_service_status}.")
            return
        time.sleep(interval)
        timed_out = int(time.time()) - start_time
        message = (
            f"Service status or state hasn't changed after {timed_out} sec."
        )
        if timed_out >= timeout:
            LOG.error(message)
            raise TimeoutError(message)


def wait_for_server_status(openstack_client, server, status):
    start_time = int(time.time())
    timeout = CONF.SERVER_TIMEOUT
    while True:
        server = openstack_client.oc.get_server(server.id)
        if server.status.upper() == status.upper():
            LOG.debug(f"Server {server.id} has status: {server.status}.")
            return
        time.sleep(CONF.SERVER_READY_INTERVAL)
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
    timeout = CONF.SERVER_TIMEOUT
    while True:
        port = openstack_client.oc.network.get_port(port.id)
        if port.status.upper() == status.upper():
            LOG.debug(f"Port {port.id} has status: {port.status}.")
            return
        time.sleep(CONF.SERVER_READY_INTERVAL)
        timed_out = int(time.time()) - start_time
        if timed_out >= timeout:
            message = (
                f"Port {port.id} failed to reach {status} "
                f"status within the required time {timeout}"
            )
            LOG.error(message)
            raise TimeoutError(message)


def wait_resource_field(
    get_resource_func, resource_id, fields, timeout, interval
):
    start_time = time.time()
    while True:
        resource = get_resource_func(resource_id)
        for field, field_value in fields.items():
            if resource.get(field) != field_value:
                time.sleep(interval)
                break
        else:
            return
        if time.time() - start_time >= timeout:
            message = f"Timed out while waiting required fields '{field}' on resource {resource}"
            LOG.error(message)
            raise TimeoutError(message)


def wait_resource_deleted(get_resource_func, resource_id, timeout, interval):
    start_time = time.time()
    try:
        while get_resource_func(resource_id):
            if time.time() - start_time >= timeout:
                message = f"Timed out while waiting for resource {resource_id} is deleted"
                LOG.error(message)
                raise TimeoutError(message)
            time.sleep(interval)
    except openstack.exceptions.ResourceNotFound:
        return


def wait_cinder_pool_updated(
    get_cinder_pool_timestamp, pool_name, last_timestamp
):
    start_time = time.time()
    timeout = CONF.CINDER_POOL_UPDATE_TIMEOUT
    while True:
        timestamp = get_cinder_pool_timestamp(pool_name)
        if timestamp > last_timestamp:
            LOG.debug(f"Cinder pool {pool_name} has updated")
            return
        time.sleep(CONF.CINDER_POOL_UPDATE_INTERVAL)
        timed_out = int(time.time()) - start_time
        if timed_out >= timeout:
            message = f"Pool {pool_name} hasn't updated within {timeout}"
            LOG.error(message)
            raise TimeoutError(message)
