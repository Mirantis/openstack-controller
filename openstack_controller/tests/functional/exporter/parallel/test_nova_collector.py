import pytest

from openstack_controller.tests.functional.exporter import base


class NovaCollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    known_metrics = {
        "osdpl_nova_service_state": {"labels": ["binary", "host", "zone"]},
        "osdpl_nova_service_status": {"labels": ["binary", "host", "zone"]},
        "osdpl_nova_instances": {"labels": []},
        "osdpl_nova_active_instances": {"labels": []},
        "osdpl_nova_error_instances": {"labels": []},
        "osdpl_nova_hypervisor_instances": {"labels": ["host", "zone"]},
        # "osdpl_nova_aggregate_hosts": {"labels": ["name"]},
        # "osdpl_nova_host_aggregate_info": {"labels": ["hosts", "name"]},
        "osdpl_nova_availability_zone_info": {"labels": ["zone"]},
        # "osdpl_nova_availability_zone_hosts": {"labels": ["zone"]},
        # "osdpl_nova_availability_zone_instances": {"labels": ["zone"]},
        # "osdpl_nova_aggregate_instances": {"osdpl_nova_aggregate_instances": ["name"]},
        "osdpl_nova_hypervisor_vcpu": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_vcpu_used": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_vcpu_free": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_vcpu_allocation_ratio": {
            "labels": ["host", "zone"]
        },
        "osdpl_nova_hypervisor_disk_gb": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_disk_gb_used": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_disk_gb_free": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_disk_gb_allocation_ratio": {
            "labels": ["host", "zone"]
        },
        "osdpl_nova_hypervisor_memory_mb": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_memory_mb_used": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_memory_mb_free": {"labels": ["host", "zone"]},
        "osdpl_nova_hypervisor_memory_mb_allocation_ratio": {
            "labels": ["host", "zone"]
        },
        # "osdpl_nova_aggregate_vcpu": {"labels": ["name"]},
        # "osdpl_nova_aggregate_vcpu_used": {"labels": ["name"]},
        # "osdpl_nova_aggregate_vcpu_free": {"labels": ["name"]},
        # "osdpl_nova_aggregate_disk_gb": {"labels": ["name"]},
        # "osdpl_nova_aggregate_disk_gb_used": {"labels": ["name"]},
        # "osdpl_nova_aggregate_disk_gb_free": {"labels": ["name"]},
        # "osdpl_nova_aggregate_memory_mb": {"labels": ["name"]},
        # "osdpl_nova_aggregate_memory_mb_used": {"labels": ["name"]},
        # "osdpl_nova_aggregate_memory_mb_free": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_vcpu_used": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_vcpu_free": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_disk_gb": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_disk_gb_used": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_disk_gb_free": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_memory_mb": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_memory_mb_used": {"labels": ["name"]},
        # "osdpl_nova_availability_zone_memory_mb_free": {"labels": ["name"]},
    }

    def setUp(self):
        super().setUp()
        self.compute_svc = self.ocm.compute_get_services(binary=None)
        self.compute_number = len(self.compute_svc)

    def test_service_state(self):
        metric = self.get_metric("osdpl_nova_service_state")
        self.assertIsNotNone(metric)
        self.assertEqual(self.compute_number, len(metric.samples))
        self.assertCountEqual(
            ["host", "zone", "binary"],
            metric.samples[0].labels.keys(),
        )

    def test_service_status(self):
        metric = self.get_metric("osdpl_nova_service_status")
        self.assertIsNotNone(metric)
        self.assertEqual(self.compute_number, len(metric.samples))
        self.assertCountEqual(
            ["host", "zone", "binary"],
            metric.samples[0].labels.keys(),
        )


@pytest.mark.xdist_group("exporter-compute-network")
class NovaCollectorInstancesFunctionalTestCase(
    base.BaseFunctionalExporterTestCase
):
    scrape_collector = "osdpl_nova"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_nova_instances(self):
        """Total number of instances in the cluster."""

        metric = self.get_metric("osdpl_nova_instances")
        servers = self.ocm.compute_get_all_servers()
        self.assertEqual(
            int(metric.samples[0].value),
            len(servers),
            f"Current numbers of servers in exporter's metric are {int(metric.samples[0].value)}."
            f"Expected numbers of active servers: {len(servers)}.",
        )

    def test_nova_active_instances(self):
        """Total number of instances in the active state in the cluster.

        **Steps:**

        #. Get exporter metric "osdpl_nova_active_instances" with initial number
        of instances in the active state in the cluster
        #. Create additional test instance in active state
        #. Check that number of active instances was changed in metrics
        #. Delete additional test instance
        #. Check that number of active instances decreased in response from exporter

        """
        metric_name = "osdpl_nova_active_instances"
        initial_metric = self.get_metric(metric_name)
        initial_active_servers = self.ocm.compute_get_all_servers(
            status="ACTIVE"
        )
        self.assertEqual(
            int(initial_metric.samples[0].value),
            len(initial_active_servers),
            f"Current numbers of active servers in exporter's metric are {int(initial_metric.samples[0].value)}."
            f"Expected numbers of active servers: {len(initial_active_servers)}.",
        )

        active_server = self.server_create()
        active_metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        active_servers = self.ocm.compute_get_all_servers(status="ACTIVE")
        self.assertEqual(
            int(active_metric.samples[0].value),
            len(active_servers),
            f"Current numbers of active servers in exporter's metrics are {int(initial_metric.samples[0].value)}."
            f"Expected numbers of active servers: {len(active_servers)}.",
        )

        self.server_delete(active_server)
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(active_servers) - 1,
            f"Current numbers of active servers in exporter's metrics are {int(initial_metric.samples[0].value)}."
            f"Expected numbers of active servers: {len(active_servers) - 1}.",
        )

    def test_nova_error_instances(self):
        """Total number of instances in the error state in the cluster.

        **Steps:**

        #. Get exporter metric "osdpl_nova_error_instances"  with initial number
        of instances in the error state in the cluster
        #. Create additional test instance in active state
        #. Reset the state of test server to 'error'
        #. Check that number of error instances was changed in response from exporter

        """
        metric_name = "osdpl_nova_error_instances"
        initial_metric = self.get_metric(metric_name)
        initial_error_servers = self.ocm.compute_get_all_servers(
            status="ERROR"
        )
        self.assertEqual(
            int(initial_metric.samples[0].value),
            len(initial_error_servers),
            f"Current numbers of error servers in exporter's metrics are {int(initial_metric.samples[0].value)}."
            f"Expected numbers of active servers: {len(initial_error_servers)}.",
        )

        error_server = self.server_create()
        self.server_reset_state(error_server, "error")
        error_servers = self.ocm.compute_get_all_servers(status="ERROR")
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )

        self.assertEqual(
            int(metric.samples[0].value),
            len(error_servers),
            f"Current numbers of error servers in exporter's metrics are {int(metric.samples[0].value)}."
            f"Expected numbers of active servers: {len(error_servers)}.",
        )

    def test_nova_availability_zone_info(self):
        """Information about availability zones in the cluster.

        **Steps**

        #. Get `osdpl_nova_availability_zone_info` metric with initial number
        #. Add additional availability zone
        #. Check that new availablity zone appear in the samples
        """
        metric_name = "osdpl_nova_availability_zone_info"
        azs = list(self.ocm.oc.compute.availability_zones())
        initial_metric = self.get_metric(metric_name)
        self.assertEqual(
            len(initial_metric.samples),
            len(azs),
            "The initial number of availability zones is not correct.",
        )

        aggregate = self.aggregate_create(
            name="test_nova_availability_zone_info",
            availability_zone="test_nova_availability_zone_info",
        )
        metric_after_create = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )

        # NOTE(vsienko): empty az is not show on API LP: 2045888
        expected_azs = len(azs)
        self.assertEqual(
            len(metric_after_create.samples),
            expected_azs,
            "The number of availability zones after create is not correct.",
        )

        self.aggregate_delete(aggregate["name"])

        metric_after_delete = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )

        self.assertEqual(
            len(metric_after_delete.samples),
            len(azs),
            "The number of availability zones after delete is not correct.",
        )
