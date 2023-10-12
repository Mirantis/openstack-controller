import logging

from kombu import Connection
from unittest import TestCase

import openstack

from openstack_controller import kube
from openstack_controller import openstack_utils
from openstack_controller.exporter import constants
from openstack_controller.tests.functional import config
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

CONF = config.Config()


def suppress404(func):
    def inner(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except openstack.exceptions.ResourceNotFound:
            pass

    return inner


class BaseFunctionalTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ocm = openstack_utils.OpenStackClientManager()
        cls.osdpl = kube.get_osdpl()

    def setUp(self):
        self.kube_api = kube.kube_client()
        self.setup_logging()

    def setup_logging(self):
        logging.setLogRecordFactory(self.logging_record_factory)

    def logging_record_factory(self, *args, **kwargs):
        record = logging_old_factory(*args, **kwargs)
        record.testMethodName = self._testMethodName
        return record

    @property
    def neturon_portprober_enabled(self):
        return (
            self.osdpl.obj["spec"]["features"]["neutron"]
            .get("extensions", {})
            .get("portprober", {})
            .get("enabled", False)
        )

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
        availability_zone=None,
        host=None,
        config_drive=None,
        user_data=None,
    ):
        kwargs = {"networks": networks}
        if name is None:
            kwargs["name"] = data_utils.rand_name()
        if flavorRef is None:
            kwargs["flavorRef"] = cls.ocm.oc.compute.find_flavor(
                CONF.TEST_FLAVOR_NAME
            ).id
        else:
            kwargs["flavorRef"] = flavorRef
        if imageRef is None:
            kwargs["imageRef"] = cls.ocm.oc.get_image_id(
                CONF.CIRROS_TEST_IMAGE_NAME
            )
        else:
            kwargs["imageRef"] = imageRef
        if availability_zone:
            kwargs["availability_zone"] = availability_zone
        if host:
            kwargs["host"] = host
        if config_drive:
            kwargs["config_drive"] = config_drive
        if user_data:
            kwargs["user_data"] = user_data

        server = cls.ocm.oc.compute.create_server(**kwargs)
        if wait is True:
            waiters.wait_for_server_status(cls.ocm, server, status="ACTIVE")
        cls.addClassCleanup(cls.server_delete, server)
        return server

    @classmethod
    @suppress404
    def server_delete(cls, server, wait=True):
        return cls.ocm.oc.delete_server(server.id, wait=wait)

    def server_reset_state(self, server, status, wait=True):
        self.ocm.oc.compute.reset_server_state(server.id, status)
        if wait is True:
            waiters.wait_for_server_status(self.ocm, server, status=status)

    @classmethod
    def lb_bundle_create(
        cls,
        name=None,
    ):
        if name is None:
            name = data_utils.rand_name()
        network = cls.network_create()
        subnet = cls.subnet_create(
            cidr=CONF.TEST_LB_SUBNET_RANGE, network_id=network["id"]
        )
        lb = cls.ocm.oc.load_balancer.create_load_balancer(
            name=name,
            vip_network_id=network["id"],
            vip_subnet_id=subnet["id"],
        )
        cls.addClassCleanup(
            waiters.wait_resource_deleted,
            cls.ocm.oc.load_balancer.get_load_balancer,
            lb["id"],
            CONF.LB_OPERATION_TIMEOUT,
            CONF.LB_OPERATION_INTERVAL,
        )
        cls.addClassCleanup(
            cls.ocm.oc.load_balancer.delete_load_balancer, lb["id"]
        )
        cls.ocm.oc.load_balancer.wait_for_load_balancer(
            lb["id"],
            interval=CONF.LB_OPERATION_INTERVAL,
            wait=CONF.LB_OPERATION_TIMEOUT,
        )
        return lb

    @classmethod
    def lb_update(cls, lb_id, admin_state_up=True):
        lb = cls.ocm.oc.load_balancer.update_load_balancer(
            lb_id, admin_state_up=admin_state_up
        )
        cls.ocm.oc.load_balancer.wait_for_load_balancer(
            lb["id"],
            status="ACTIVE",
            interval=CONF.LB_OPERATION_INTERVAL,
            wait=CONF.LB_OPERATION_TIMEOUT,
        )

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
    @suppress404
    def network_delete(cls, network):
        return cls.ocm.oc.network.delete_network(network)

    @classmethod
    def subnet_create(
        cls,
        cidr,
        network_id,
        ip_version=4,
        name=None,
        **kwargs,
    ):
        if name is None:
            name = data_utils.rand_name()
        subnet = cls.ocm.oc.network.create_subnet(
            name=name,
            cidr=cidr,
            network_id=network_id,
            ip_version=ip_version,
            **kwargs,
        )
        cls.addClassCleanup(cls.subnet_delete, subnet)
        return subnet

    @classmethod
    @suppress404
    def subnet_delete(cls, subnet):
        return cls.ocm.oc.network.delete_subnet(subnet)

    @classmethod
    def port_create(
        cls,
        network_id,
        name=None,
        wait=True,
        status="DOWN",
        fixed_ips=None,
    ):
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
    @suppress404
    def port_delete(cls, port):
        return cls.ocm.oc.network.delete_port(port)

    @classmethod
    def floating_ip_create(cls, network):
        fip = cls.ocm.oc.create_floating_ip()
        fip_id = fip["id"]
        cls.addClassCleanup(cls.floating_ip_delete, fip_id)
        return fip

    @classmethod
    @suppress404
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
    @suppress404
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
    def routers_availability_zones(cls, availability_zones):
        routers = []
        for router in list(cls.ocm.oc.network.routers()):
            if router["availability_zones"][0] == availability_zones:
                routers.append(router)
        return routers

    @classmethod
    def network_bundle_create(cls):
        """Create network bundle and return metadata

        Creates bundle of router, subnet, network connected to flaoting network.
        """
        res = {}
        network = cls.network_create()
        subnet = cls.subnet_create(
            cidr=CONF.TEST_SUBNET_RANGE, network_id=network["id"]
        )
        res["network"] = network
        res["subnet"] = subnet
        public_network = cls.ocm.oc.network.find_network(
            CONF.PUBLIC_NETWORK_NAME
        )
        router = cls.router_create(
            external_gateway_info={"network_id": public_network["id"]}
        )
        res["router"] = router
        cls.ocm.oc.network.add_interface_to_router(
            router["id"], subnet_id=subnet["id"]
        )

        return res

    @classmethod
    def volume_create(
        cls,
        size=None,
        name=None,
        image=None,
        availability_zone=None,
        wait=True,
        timeout=None,
    ):
        if name is None:
            name = data_utils.rand_name()
        if size is None:
            size = CONF.VOLUME_SIZE
        if timeout is None:
            timeout = CONF.VOLUME_TIMEOUT

        volume = cls.ocm.oc.volume.create_volume(
            size=size,
            name=name,
            image_id=image,
            availability_zone=availability_zone,
            wait=wait,
            timeout=timeout,
        )
        cls.addClassCleanup(cls.volume_delete, volume)
        if wait is True:
            waiters.wait_resource_field(
                cls.ocm.oc.block_storage.get_volume,
                volume.id,
                {"status": "available"},
                timeout,
                CONF.VOLUME_READY_INTERVAL,
            )
        return volume

    @classmethod
    @suppress404
    def volume_delete(cls, volume, wait=False):
        cls.ocm.oc.delete_volume(volume.id)
        if wait:
            waiters.wait_resource_deleted(
                cls.ocm.oc.get_volume, volume.id, CONF.VOLUME_TIMEOUT, 5
            )

    @classmethod
    def get_volumes_size(cls):
        """Calculate the total size of volumes in bytes."""
        total_bytes = 0
        for volume in cls.ocm.oc.volume.volumes(all_tenants=True):
            total_bytes += volume.size * constants.Gi
        return total_bytes

    @classmethod
    def volume_snapshot_create(
        cls,
        volume,
        name=None,
    ):
        if name is None:
            name = data_utils.rand_name()

        snapshot = cls.ocm.oc.create_volume_snapshot(
            volume.id,
        )
        cls.addClassCleanup(cls.snapshot_volume_delete, snapshot)
        return snapshot

    @classmethod
    def snapshot_volume_delete(cls, snapshot, wait=False):
        cls.ocm.oc.delete_volume_snapshot(snapshot.id)
        if wait:
            waiters.wait_resource_deleted(
                cls.ocm.oc.get_volume_snapshot,
                snapshot.id,
                CONF.VOLUME_TIMEOUT,
                5,
            )

    @classmethod
    def get_volume_snapshots_size(cls):
        """Calculate the total size of volume snapshots in bytes."""
        total_bytes = 0
        for snapshot in cls.ocm.oc.list_volume_snapshots():
            total_bytes += snapshot.size * constants.Gi
        return total_bytes

    @classmethod
    @suppress404
    def aggregate_delete(cls, name):
        cls.ocm.oc.delete_aggregate(name)

    @classmethod
    def aggregate_create(cls, name, availability_zone=None):
        aggregate = cls.ocm.oc.compute.create_aggregate(
            name=name, availability_zone=availability_zone
        )
        cls.addClassCleanup(cls.aggregate_delete, name)
        return aggregate

    @classmethod
    @suppress404
    def aggregate_remove_host(cls, name, host):
        cls.ocm.oc.compute.remove_host_from_aggregate(name, host)

    @classmethod
    @suppress404
    def aggregate_remove_hosts(cls, name):
        aggregate = cls.ocm.oc.compute.get_aggregate(name)
        for host in aggregate["hosts"]:
            cls.ocm.oc.compute.remove_host_from_aggregate(
                aggregate["id"], host
            )

    @classmethod
    def aggregate_add_host(cls, name, host):
        cls.ocm.oc.compute.add_host_to_aggregate(name, host)
        cls.addClassCleanup(cls.aggregate_remove_host, name, host)

    @classmethod
    def service_create(cls, name, type):
        service = cls.ocm.oc.identity.create_service(name=name, type=type)
        cls.addClassCleanup(cls.service_delete, service["id"])
        return service

    @classmethod
    def endpoint_create(cls, service_id, interface, url):
        endpoint = cls.ocm.oc.identity.create_endpoint(
            service_id=service_id, interface=interface, url=url
        )
        cls.addClassCleanup(cls.endpoint_delete, endpoint["id"])
        return endpoint

    @classmethod
    @suppress404
    def service_delete(cls, service_id):
        cls.ocm.oc.identity.delete_service(service_id)

    @classmethod
    @suppress404
    def endpoint_delete(cls, endpoint):
        cls.ocm.oc.identity.delete_endpoint(endpoint)

    @classmethod
    def create_domain(cls, name, enabled=False):
        domain = cls.ocm.oc.identity.create_domain(name=name, enabled=enabled)
        cls.addClassCleanup(cls.delete_domain, domain["id"])
        return domain

    @classmethod
    @suppress404
    def delete_domain(cls, domain_id):
        cls.ocm.oc.identity.delete_domain(domain_id)

    def get_ports_by_status(self, status):
        ports = []
        for port in self.ocm.oc.network.ports():
            if port["status"] == status:
                ports.append(port)
        return ports

    def get_volume_service_status(self, svc):
        service = self.ocm.volume_get_services(
            host=svc["host"], binary=svc["binary"]
        )
        return service[0]["status"]

    def get_compute_service_state(self, svc):
        service = self.ocm.oc.compute.find_service(name_or_id=svc["id"])
        return service["state"]

    def get_compute_service_status(self, svc):
        service = self.ocm.oc.compute.find_service(name_or_id=svc["id"])
        return service["status"]

    def get_neutron_agent_status(self, svc):
        agent = self.ocm.oc.network.get_agent(svc["id"])
        return agent["is_admin_state_up"]

    def get_cinder_pool_timestamp(self, pool_name):
        pool = [
            pl
            for pl in list(self.ocm.oc.volume.backend_pools())
            if pl["name"] == pool_name
        ]
        return pool[0]["capabilities"].get("timestamp")

    def get_portprober_agent(self, host=None):
        return list(
            self.ocm.oc.network.agents(
                host=host, binary="neutron-portprober-agent"
            )
        )

    def get_portprober_networks(self, agent_id):
        return self.ocm.oc.network.get(
            f"/agents/{agent_id}/portprober-networks"
        ).json()["networks"]

    def get_agents_hosting_portprober_network(self, network_id):
        res = []
        for agent in self.get_portprober_agent():
            agent_nets = self.get_portprober_networks(agent["id"])
            for network in agent_nets:
                if network["id"] == network_id:
                    res.append(agent)
                    continue
        return res
