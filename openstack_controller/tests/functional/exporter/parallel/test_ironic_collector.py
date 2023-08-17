from openstack_controller.tests.functional.exporter import base


class IronicCollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    def setUp(self):
        super().setUp()

    def is_baremetal_enabled(self):
        return "baremetal" in self.osdpl.obj["spec"]["features"].get(
            "services", []
        )

    def test_total_nodes_metric_present(self):
        metric = self.get_metric("osdpl_ironic_nodes")
        if self.is_baremetal_enabled():
            self.assertIsNotNone(metric)
            self.assertEqual(1, len(metric.samples))
        else:
            self.assertIsNone(metric)

    def test_total_nodes_value(self):
        metric = self.get_metric("osdpl_ironic_nodes")
        baremetal_nodes = 0
        if self.is_baremetal_enabled():
            baremetal_nodes = len(list(self.ocm.oc.baremetal.nodes()))
            self.assertEqual(baremetal_nodes, metric.samples[0].value)

            self.assertCountEqual(
                [],
                metric.samples[0].labels.keys(),
            )
