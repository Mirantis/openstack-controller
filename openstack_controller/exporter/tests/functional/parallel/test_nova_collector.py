from openstack_controller.exporter.tests.functional import base


class NovaCollectorFunctionalTestCase(base.BaseFunctionalTestCase):
    def setUp(self):
        super().setUp()
        self.compute_svc = self.ocm.compute_get_services()
        self.compute_number = len(self.compute_svc)

    def test_service_state(self):
        metric = self.get_metric("osdpl_nova_service_state")
        self.assertIsNotNone(metric)
        self.assertEqual(self.compute_number * 2, len(metric.samples))
        self.assertCountEqual(
            ["osdpl_nova_service_state", "host", "osdpl", "binary"],
            metric.samples[0].labels.keys(),
        )

    def test_service_state_value(self):
        for service in self.compute_svc:
            labels = {
                "osdpl_nova_service_state": service["state"],
                "host": service["host"],
                "binary": service["binary"],
            }
            metric = self.get_metric("osdpl_nova_service_state")
            service_samples = self.filter_metric_samples(metric, labels)
            self.assertEqual(1, len(service_samples))
            self.assertEqual(1, service_samples[0].value)

    def test_service_status(self):
        metric = self.get_metric("osdpl_nova_service_status")
        self.assertIsNotNone(metric)
        self.assertEqual(self.compute_number * 2, len(metric.samples))
        self.assertCountEqual(
            ["osdpl_nova_service_status", "host", "osdpl", "binary"],
            metric.samples[0].labels.keys(),
        )

    def test_service_status_value(self):
        for service in self.compute_svc:
            labels = {
                "osdpl_nova_service_status": service["status"],
                "host": service["host"],
                "binary": service["binary"],
            }
            metric = self.get_metric("osdpl_nova_service_status")
            service_samples = self.filter_metric_samples(metric, labels)
            self.assertEqual(1, len(service_samples))
            self.assertEqual(1, service_samples[0].value)
