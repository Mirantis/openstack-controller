from parameterized import parameterized
import pytest

from openstack_controller.exporter import constants
from openstack_controller.tests.functional.exporter import base
from openstack_controller.tests.functional import config


CONF = config.Config()


@pytest.mark.xdist_group("exporter-volume")
class CinderCollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    scrape_collector = "osdpl_cinder"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    known_metrics = {
        "osdpl_cinder_snapshots": {"labels": []},
        "osdpl_cinder_pool_free_capacity": {"labels": ["name"]},
        "osdpl_cinder_pool_total_capacity": {"labels": ["name"]},
    }

    @pytest.mark.xdist_group("exporter-volume")
    def test_volume_snapshots(self):
        """Total number of volume snapshots in the cluster."""

        metric_name = "osdpl_cinder_snapshots"
        initial_metric = self.get_metric(metric_name)
        snapshots = self.ocm.oc.list_volume_snapshots()
        self.assertEqual(
            int(initial_metric.samples[0].value),
            len(snapshots),
            "The initial number of snapshots is not correct.",
        )

        # Create one test volume and one volume snapshot
        volume = self.volume_create()
        snapshot = self.volume_snapshot_create(volume)
        active_metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )

        # Check that a volume's snapshot metric is changed
        snapshots = self.ocm.oc.list_volume_snapshots()
        self.assertEqual(
            int(active_metric.samples[0].value),
            len(snapshots),
            "The number of volume snapshots after create is not correct",
        )

        # Delete Volume's snapshot and check that a volume's snapshot metric is changed
        self.snapshot_volume_delete(snapshot, wait=True)
        metric = self.get_metric_after_refresh(
            metric_name, self.scrape_collector
        )
        self.assertEqual(
            int(metric.samples[0].value),
            len(snapshots) - 1,
            "The number of volume snapshots after delete is not correct",
        )

    @parameterized.expand(
        [
            ("osdpl_cinder_pool_free_capacity"),
            ("osdpl_cinder_pool_total_capacity"),
            ("osdpl_cinder_pool_allocated_capacity"),
        ]
    )
    def test_openstack_cinder_pool_samples_count(self, metric_name):
        total_pools = len(list(self.ocm.oc.volume.backend_pools()))
        metric = self.get_metric(metric_name)
        self.assertEqual(
            len(metric.samples),
            total_pools,
            "The number of samples for {metric_name} is not correct.",
        )

    def _test_cinder_pool_metric(
        self, metric_name, pool_name, expected_value, phase
    ):
        associated_metric = self.filter_metric_samples(
            self.get_metric(metric_name), {"name": pool_name}
        )
        self.assertEqual(
            associated_metric[0].value,
            expected_value,
            f"{phase}: The expected value for {metric_name} for pool {pool_name} is not correct.",
        )

    @pytest.mark.xdist_group("exporter-volume")
    def test_openstack_cinder_pool_total_capacity(self):
        """Total capacity in bytes of cinder backend pools in environment."""

        metric_name = "osdpl_cinder_pool_total_capacity"
        for pool in self.ocm.oc.volume.backend_pools():
            pool_name = pool["name"]
            capacity = pool["capabilities"].get("total_capacity_gb") * (
                constants.Gi
            )

            self._test_cinder_pool_metric(
                metric_name, pool_name, capacity, "Before create"
            )
            self.volume_create(size=5, image=CONF.CIRROS_TEST_IMAGE_NAME)
            self._test_cinder_pool_metric(
                metric_name, pool_name, capacity, "After create"
            )

    @pytest.mark.skip(reason="unless is fixed PRODX-38532")
    @pytest.mark.xdist_group("exporter-volume")
    def test_openstack_cinder_pool_free_capacity(self):
        """Free capacity in bytes of cinder backend pools in environment."""

        metric_name = "osdpl_cinder_pool_free_capacity"
        for pool in self.ocm.oc.volume.backend_pools():
            pool_name = pool["name"]
            capacity = pool["capabilities"].get("free_capacity_gb") * (
                constants.Gi
            )

            self._test_cinder_pool_metric(
                metric_name, pool_name, capacity, "Before create empty volume"
            )
            self.volume_create(size=5)
            self._test_cinder_pool_metric(
                metric_name, pool_name, capacity, "After create empty volume"
            )

            image = self.ocm.oc.image.find_image(CONF.UBUNTU_TEST_IMAGE_NAME)

            # Ubuntu image is approx 300Mb in size, create 5 volumes to consume 1Gb for sure
            for i in range(0, 5):
                self.volume_create(size=1, image=CONF.UBUNTU_TEST_IMAGE_NAME)

            self._test_cinder_pool_metric(
                metric_name,
                pool_name,
                capacity - image["size"] * constants.Gi,
                "After create empty volume",
            )

    @pytest.mark.skip(reason="unless is fixed PRODX-38531")
    @pytest.mark.xdist_group("exporter-volume")
    def test_openstack_cinder_pool_allocated_capacity(self):
        """Allocated capacity in bytes of cinder backend pools in environment."""

        metric_name = "osdpl_cinder_pool_allocated_capacity"
        for pool in self.ocm.oc.volume.backend_pools():
            pool_name = pool["name"]
            capacity = pool["capabilities"].get("allocated_capacity_gb") * (
                constants.Gi
            )

            self._test_cinder_pool_metric(
                metric_name, pool_name, capacity, "Before create"
            )
            self.volume_create(size=5, image=CONF.CIRROS_TEST_IMAGE_NAME)
            self._test_cinder_pool_metric(
                metric_name,
                pool_name,
                capacity - 5 * constants.Gi,
                "After create",
            )
