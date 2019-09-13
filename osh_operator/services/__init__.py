from osh_operator import layers
from osh_operator import openstack
from .base import Service

# INFRA SERVICES


class Ingress(Service):
    service = "ingress"


class MariaDB(Service):
    service = "database"

    def template_args(self, spec):
        admin_creds = openstack.get_admin_credentials(self.namespace)
        return {"admin_creds": admin_creds}


class Memcached(Service):
    service = "memcached"


class RabbitMQ(Service):
    service = "messaging"

    def template_args(self, spec):
        credentials = {}
        admin_creds = openstack.get_admin_credentials(self.namespace)
        services = set(spec["features"]["services"]) - set(["tempest"])
        for s in services:
            if s not in openstack.OS_SERVICES_MAP:
                continue
            # TODO: 'use get or wait' approach for generated credential here
            credentials[s] = openstack.get_or_create_os_credentials(
                s, self.namespace
            )

        return {
            "services": services,
            "credentials": credentials,
            "admin_creds": admin_creds,
        }


# OPENSTACK SERVICES


class Barbican(Service):
    service = "key-manager"


class Cinder(Service):
    ceph_required = True
    service = "block-storage"


class Designate(Service):
    service = "dns"


class Glance(Service):
    ceph_required = True
    service = "image"


class Heat(Service):
    service = "orchestration"


class Horizon(Service):
    service = "dashboard"


class Keystone(Service):
    service = "identity"


class Neutron(Service):
    service = "networking"


class Nova(Service):
    service = "compute"
    ceph_required = True


class Octavia(Service):
    service = "load-balancer"


class RadosGateWay(Service):
    service = "object-storage"


class Tempest(Service):
    service = "tempest"

    def template_args(self, spec):
        # TODO: add wait for generated credential here
        admin_creds = openstack.get_admin_credentials(self.namespace)
        helmbundles_body = {}
        for s in set(spec["features"]["services"]) - {"tempest"}:
            service_creds = openstack.get_or_create_os_credentials(
                s, self.namespace
            )
            helmbundles_body[s] = layers.merge_all_layers(
                s,
                self.osdpl.obj,
                self.osdpl.metadata,
                spec,
                self.logger,
                credentials=service_creds,
                admin_creds=admin_creds,
            )
        return {
            "helmbundles_body": helmbundles_body,
            "admin_creds": admin_creds,
        }


registry = Service.registry
