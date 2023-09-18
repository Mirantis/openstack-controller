from openstack_controller.tests.functional.exporter import base


class OsdplCollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    def test_heat_stacks(self):
        metric = self.get_metric("osdpl_heat_stacks")
        stacks = len(list(self.ocm.oc.orchestration.stacks()))
        self.assertIsNotNone(metric)
        self.assertEqual(1, len(metric.samples))
        self.assertEqual(int(metric.samples[0].value), stacks)
