import pytest

from openstack_controller.tests.functional.exporter import base


@pytest.mark.xdist_group("exporter-volume")
class CinderCollectorSnapshotsFunctionalTestCase(
    base.BaseFunctionalExporterTestCase
):
    scrape_collector = "osdpl_cinder"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    known_metrics = {
        "osdpl_cinder_snapshots": {"labels": []},
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
