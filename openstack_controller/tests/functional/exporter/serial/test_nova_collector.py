from openstack_controller.tests.functional.exporter import base


class NovaCollectorSerialFunctionalTestCase(base.BaseFunctionalTestCase):
    def setUp(self):
        super().setUp()
        svc = [
            svc
            for svc in self.ocm.compute_get_services()
            if svc["status"].lower() == "enabled"
        ][0]

        self.compute_svc_data = {"host": svc["host"], "binary": svc["binary"]}

    @property
    def compute_svc(self):
        return self.ocm.compute_get_services(**self.compute_svc_data)[0]

    def tearDown(self):
        self.ocm.compute_ensure_service_enabled(self.compute_svc)
        self.ocm.compute_ensure_service_force_down(self.compute_svc, False)
        super().tearDown()

    def test_service_status(self):
        metric = self.get_metric("osdpl_nova_service_status")
        labels = {
            "osdpl_nova_service_status": "enabled",
            "host": self.compute_svc["host"],
            "binary": self.compute_svc["binary"],
        }
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(1.0, service_samples[0].value)
        labels["osdpl_nova_service_status"] = "disabled"
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(0.0, service_samples[0].value)

    def test_service_status_disable(self):
        self.ocm.compute_ensure_service_disabled(
            self.compute_svc, "Functional test test_service_status_disable"
        )
        labels = {
            "osdpl_nova_service_status": "enabled",
            "host": self.compute_svc["host"],
            "binary": self.compute_svc["binary"],
        }
        metric = self.get_metric("osdpl_nova_service_status")
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(0.0, service_samples[0].value)
        labels["osdpl_nova_service_status"] = "disabled"
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(1.0, service_samples[0].value)

    def test_service_state(self):
        metric = self.get_metric("osdpl_nova_service_state")
        labels = {
            "osdpl_nova_service_state": "up",
            "host": self.compute_svc["host"],
            "binary": self.compute_svc["binary"],
        }
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(1.0, service_samples[0].value)
        labels["osdpl_nova_service_state"] = "down"
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(0.0, service_samples[0].value)

    def test_service_state_down(self):
        self.ocm.compute_ensure_service_force_down(self.compute_svc, True)
        labels = {
            "osdpl_nova_service_state": "down",
            "host": self.compute_svc["host"],
            "binary": self.compute_svc["binary"],
        }
        metric = self.get_metric("osdpl_nova_service_state")
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(0.0, service_samples[0].value)
        labels["osdpl_nova_service_state"] = "up"
        service_samples = self.filter_metric_samples(metric, labels)
        self.assertEqual(1, len(service_samples))
        self.assertEqual(1.0, service_samples[0].value)
