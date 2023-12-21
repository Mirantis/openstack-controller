from openstack_controller.tests.functional.exporter import base


class CredentialsCollectorFunctionalTestCase(
    base.BaseFunctionalExporterTestCase
):
    def setUp(self):
        super().setUp()
        self.metric = self.get_metric("osdpl_credentials_rotation_timestamp")

    def test_metric_present(self):
        self.assertIsNotNone(self.metric)

    def test_rotation_samples(self):
        for _type in ["admin", "service"]:
            labels = {"type": _type}
            samples = self.filter_metric_samples(self.metric, labels)
            self.assertEqual(1, len(samples))
