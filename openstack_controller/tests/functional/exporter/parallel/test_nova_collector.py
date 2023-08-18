from openstack_controller.tests.functional.exporter import base


class NovaCollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    def setUp(self):
        super().setUp()
        self.compute_svc = self.ocm.compute_get_services()
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
