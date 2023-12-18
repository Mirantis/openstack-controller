import pytest

from openstack_controller.tests.functional.exporter import base
from openstack_controller.tests.functional import config as conf


@pytest.mark.xdist_group("exporter-compute-network")
class NeutronCollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    scrape_collector = "osdpl_neutron"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        bundle = cls.network_bundle_create()
        cls.network = bundle["network"]
        cls.subnet = bundle["subnet"]
        cls.router = bundle["router"]
        cls.servers = []

    known_metrics = {
        "osdpl_neutron_networks": {"labels": []},
        "osdpl_neutron_subnets": {"labels": []},
        "osdpl_neutron_down_ports": {"labels": []},
        "osdpl_neutron_ports": {"labels": []},
        "osdpl_neutron_routers": {"labels": []},
        "osdpl_neutron_floating_ips": {"labels": ["state"]},
        "osdpl_neutron_availability_zone_info": {
            "labels": ["zone", "resource"]
        },
    }

    def test_neutron_networks(self):
        """Total number of networks in the cluster.


        **Steps:**

        #. Get exporter metric "osdpl_neutron_networks"  with initial number
        of networks in the cluster
        #. Check that number of networks is equal for OS and exporter
        #. Create additional test network
        #. Check that number of networks was changed in response from exporter
        #. Delete the created network
        #. Check that number of networks was changed in response from exporter

        """
        metric_name = "osdpl_neutron_networks"
        metric = self.get_metric(metric_name)
        networks = list(self.ocm.oc.network.networks())
        self.assertEqual(
            int(metric.samples[0].value),
            len(networks),
            "The initial number of networks is not correct.",
        )
        network = self.network_create()
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(networks) + 1,
            "The number of networks after network create is not correct.",
        )
        self.network_delete(network)
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(networks),
            "The number of networks after network delete is not correct.",
        )

    def test_neutron_subnets(self):
        """Total number of subnets in the cluster.


        **Steps:**

        #. Get exporter metric "osdpl_neutron_subnets"  with initial number
        of subnets in the cluster
        #. Check that number of subnets is equal for OS and exporter
        #. Create additional test subnet
        #. Check that number of subnets was changed in response from exporter
        #. Delete the created subnet
        #. Check that number of subnets was changed in response from exporter

        """
        metric_name = "osdpl_neutron_subnets"
        metric = self.get_metric(metric_name)
        subnets = list(self.ocm.oc.network.subnets())
        self.assertEqual(
            int(metric.samples[0].value),
            len(subnets),
            "The initial number of subnets is not correct.",
        )
        subnet = self.subnet_create(
            cidr="192.168.0.0/24", network_id=self.network["id"]
        )
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(subnets) + 1,
            "The number of subnets after subnet create is not correct.",
        )
        self.subnet_delete(subnet)
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(subnets),
            "The number of subnets after subnet delete is not correct.",
        )

    def test_neutron_ports(self):
        """Total number of ports in the cluster."""
        metric_name = "osdpl_neutron_ports"
        initial_metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        ports = list(self.ocm.oc.network.ports())
        self.assertEqual(
            int(initial_metric.samples[0].value),
            len(ports),
            "The initial number of ports is not correct",
        )

        down_port = self.port_create(self.network["id"])
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(ports) + 1,
            "The number of ports after port create is not correct.",
        )

        self.port_delete(down_port)
        metric_after_delete_port = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric_after_delete_port.samples[0].value),
            len(ports),
            "The number of ports after port delete is not correct.",
        )

    def check_fips_metrics(self, total, associated, not_associated, phase):
        metric_name = "osdpl_neutron_floating_ips"
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        not_associated_metric = self.filter_metric_samples(
            metric, {"state": "not_associated"}
        )
        associated_metric = self.filter_metric_samples(
            metric, {"state": "associated"}
        )
        total_fips = int(self.sum_metric_samples(metric))
        self.assertEqual(
            total_fips,
            total,
            f"{phase}: The numbner of Fips is not correct",
        )

        self.assertEqual(
            not_associated_metric[0].value,
            not_associated,
            f"{phase}: The numbner of not associated FIPs is not correct.",
        )

        self.assertEqual(
            associated_metric[0].value,
            associated,
            f"{phase}: The numbner of associated FIPs is not correct.",
        )
        self.assertEqual(
            associated_metric[0].value + not_associated_metric[0].value,
            total,
            f"{phase}: The summ of associated and not associated does not match expected total.",
        )

    def test_neutron_floating_ips(self):
        """Total number FIPs


        **Steps:**

        #. Get exporter metric "osdpl_neutron_floating_ips"  with initial number
        of fips in the cluster
        #. Check that number of fips is equal for OS and exporter
        #. Create additional test fip
        #. Check that number of not_associated fips was changed in response from exporter
        #. Associate FIP with port
        #. Check that number associated fips increased

        """
        fips = len(self.ocm.oc.list_floating_ips())
        fips_associated = self.floating_ips_associated()

        self.check_fips_metrics(
            fips, fips_associated, fips - fips_associated, "Initial"
        )

        fip = self.floating_ip_create(conf.PUBLIC_NETWORK_NAME)

        fips = fips + 1
        self.check_fips_metrics(
            fips, fips_associated, fips - fips_associated, "Create"
        )

        fixed_ips = [{"subnet_id": self.subnet["id"]}]
        port = self.port_create(self.network["id"], fixed_ips=fixed_ips)
        self.ocm.network_floating_ip_update(
            fip["id"], data={"port_id": port["id"]}
        )

        self.check_fips_metrics(
            fips, fips_associated + 1, fips - fips_associated - 1, "Associate"
        )

    def test_neutron_routers(self):
        """Total number of routers in the cluster."""
        metric_name = "osdpl_neutron_routers"
        initial_metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        routers = list(self.ocm.oc.network.routers())
        self.assertEqual(
            int(initial_metric.samples[0].value),
            len(routers),
            "The initial number of routers is not correct",
        )

        router = self.router_create()
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(routers) + 1,
            "The number of routers after router create is not correct.",
        )

        self.router_delete(router)
        metric_after_delete_router = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric_after_delete_router.samples[0].value),
            len(routers),
            "The number of routers after router delete is not correct.",
        )


class NeutronAvailabilityZoneTestCase(base.BaseFunctionalExporterTestCase):
    def test_neutron_availability_zone_info(self):
        """Information about neutron availability zones in the cluster.

        **Steps**

        #. Get `osdpl_neutron_availability_zone_info` metric
        #. Get info about neutron's availability zones from OS
        #. Compare exporter's metrics and info from OS
        """
        metric_name = "osdpl_neutron_availability_zone_info"
        neutron_az = list(self.ocm.oc.network.availability_zones())
        metric = self.get_metric(metric_name)

        self.assertEqual(
            len(metric.samples),
            len(neutron_az),
            "The initial number of neutrone's availability zones is not correct.",
        )

        for availability_zone in neutron_az:
            labels = {
                "resource": availability_zone.resource,
                "zone": availability_zone.name,
            }
            samples = self.filter_metric_samples(metric, labels)
            self.assertDictEqual(
                samples[0].labels,
                labels,
                "The info about AZ in exporter's metrics is not correct.",
            )
            self.assertEqual(
                samples[0].value,
                1.0,
                "The info about AZ in exporter's metrics is not correct.",
            )
