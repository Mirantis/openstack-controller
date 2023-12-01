import logging

from kombu import Connection
from unittest import TestCase

import openstack

from openstack_controller import kube
from openstack_controller import openstack_utils
from openstack_controller.tests.functional import config as conf
from openstack_controller.tests.functional import data_utils, waiters

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "aiohttp": {
            "level": "WARNING",
        },
        "stevedore": {
            "level": "INFO",
        },
        "urllib3": {
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["default"],
        "level": "DEBUG",
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logging_old_factory = logging.getLogRecordFactory()
LOG = logging.getLogger(__name__)


class BaseFunctionalTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocm = openstack_utils.OpenStackClientManager()

    def setUp(self):
        self.kube_api = kube.kube_client()
        self.osdpl = kube.get_osdpl()
        self.setup_logging()

    def setup_logging(self):
        logging.setLogRecordFactory(self.logging_record_factory)

    def logging_record_factory(self, *args, **kwargs):
        record = logging_old_factory(*args, **kwargs)
        record.testMethodName = self._testMethodName
        return record

    def is_service_enabled(self, name):
        return name in self.osdpl.obj["spec"].get("features", {}).get(
            "services", []
        )

    def check_rabbitmq_connection(
        self, username, password, host, port, vhost, ssl=False
    ):
        rabbitmq_url = f"amqp://{username}:{password}@{host}:{port}/{vhost}"
        connection = Connection(rabbitmq_url, ssl=ssl)
        try:
            LOG.info(f"Connecting to the: {rabbitmq_url}")
            connection.ensure_connection(max_retries=3)
            connection.channel()
            return True
        except Exception as e:
            LOG.error(f"Connection error. Error: {e}")
        finally:
            connection.release()

    @classmethod
    def server_create(
        cls,
        wait=True,
        name=None,
        flavorRef=None,
        imageRef=None,
        networks="none",
    ):
        if name is None:
            name = data_utils.rand_name()
        if flavorRef is None:
            flavorRef = cls.ocm.oc.compute.find_flavor(conf.TEST_FLAVOR_NAME)
        if imageRef is None:
            imageRef = cls.ocm.oc.get_image_id(conf.CIRROS_TEST_IMAGE_NAME)

        server = cls.ocm.oc.compute.create_server(
            name=name,
            imageRef=imageRef,
            flavorRef=flavorRef.id,
            networks=networks,
            wait=wait,
        )
        if wait is True:
            waiters.wait_for_server_status(cls.ocm, server, status="ACTIVE")
        cls.addClassCleanup(cls.server_delete, server)
        return server

    @classmethod
    def server_delete(cls, server, wait=True):
        return cls.ocm.oc.delete_server(server.id, wait=wait)

    def server_reset_state(self, server, status, wait=True):
        self.ocm.oc.compute.reset_server_state(server.id, status)
        if wait is True:
            waiters.wait_for_server_status(self.ocm, server, status=status)

    @classmethod
    def network_create(
        cls,
        name=None,
    ):
        if name is None:
            name = data_utils.rand_name()

        network = cls.ocm.oc.network.create_network(name=name)
        cls.addClassCleanup(cls.network_delete, network)
        return network

    @classmethod
    def network_delete(cls, network):
        return cls.ocm.oc.network.delete_network(network)

    @classmethod
    def subnet_create(
        cls,
        cidr,
        network_id,
        ip_version=4,
        name=None,
    ):
        if name is None:
            name = data_utils.rand_name()

        subnet = cls.ocm.oc.network.create_subnet(
            name=name, cidr=cidr, network_id=network_id, ip_version=ip_version
        )
        cls.addClassCleanup(cls.subnet_delete, subnet)
        return subnet

    @classmethod
    def subnet_delete(cls, subnet):
        return cls.ocm.oc.network.delete_subnet(subnet)

    @classmethod
    def port_create(
        cls,
        network_id=None,
        name=None,
        wait=True,
        status="DOWN",
        fixed_ips=None,
    ):
        if network_id is None:
            network_id = cls.ocm.oc.get_network(conf.TEST_NETWORK_NAME)["id"]

        if name is None:
            name = data_utils.rand_name()
        kwargs = {"name": name, "network_id": network_id}
        if fixed_ips:
            kwargs.update({"fixed_ips": fixed_ips})

        port = cls.ocm.oc.network.create_port(**kwargs)
        if wait is True:
            waiters.wait_for_port_status(cls.ocm, port, status=status)
        cls.addClassCleanup(cls.port_delete, port)
        return port

    @classmethod
    def port_delete(cls, port):
        return cls.ocm.oc.network.delete_port(port)

    @classmethod
    def floating_ip_create(cls, network):
        fip = cls.ocm.oc.create_floating_ip()
        fip_id = fip["id"]
        cls.addClassCleanup(cls.floating_ip_delete, fip_id)
        return fip

    @classmethod
    def floating_ip_delete(cls, fip_id):
        cls.ocm.oc.delete_floating_ip(fip_id)

    @classmethod
    def floating_ips_associated(cls):
        res = 0
        for fip in cls.ocm.oc.list_floating_ips():
            if fip.get("port_id") is not None:
                res += 1
        return res

    @classmethod
    def floating_ips_not_associated(cls):
        res = 0
        for fip in cls.ocm.oc.list_floating_ips():
            if fip.get("port_id") is None:
                res += 1
        return res

    @classmethod
    def router_delete(cls, router_id):
        for port in cls.ocm.oc.network.ports(device_id=router_id):
            try:
                cls.ocm.oc.network.remove_interface_from_router(
                    router_id, port_id=port["id"]
                )
            except openstack.exceptions.ResourceNotFound:
                pass
        cls.ocm.oc.network.delete_router(router_id)

    @classmethod
    def router_create(cls, name=None, external_gateway_info=None):
        if name is None:
            name = data_utils.rand_name()
        kwargs = {"name": name}
        if external_gateway_info:
            kwargs["external_gateway_info"] = external_gateway_info

        router = cls.ocm.oc.network.create_router(**kwargs)
        cls.addClassCleanup(cls.router_delete, router["id"])
        return router

    @classmethod
    def network_bundle_create(cls):
        """Create network bundle and return metadata

        Creates bundle of router, subnet, network connected to flaoting network.
        """
        res = {}
        network = cls.network_create()
        subnet = cls.subnet_create(
            cidr=conf.TEST_SUBNET_RANGE, network_id=network["id"]
        )
        res["network"] = network
        res["subnet"] = subnet
        public_network = cls.ocm.oc.network.find_network(
            conf.PUBLIC_NETWORK_NAME
        )
        router = cls.router_create(
            external_gateway_info={"network_id": public_network["id"]}
        )
        res["router"] = router
        cls.ocm.oc.network.add_interface_to_router(
            router["id"], subnet_id=subnet["id"]
        )

        return res
