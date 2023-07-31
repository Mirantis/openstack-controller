from openstack_controller.exporter.tests.functional import base


class OsdplCollectprFunctionalTestCase(base.BaseFunctionalTestCase):
    def test_openstack_version(self):
        metric = self.get_metric("osdpl_version_info")
        self.assertIsNotNone(metric)
        self.assertEqual(1, len(metric.samples))
        self.assertCountEqual(
            ["openstack_version", "osdpl"], metric.samples[0].labels.keys()
        )
