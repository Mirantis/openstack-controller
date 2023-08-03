from openstack_controller.exporter.tests.functional import base


class GlanceCollectorFunctionalTestCase(base.BaseFunctionalTestCase):
    def test_osdpl_glance_images(self):
        metric = self.get_metric("osdpl_glance_images")
        self.assertIsNotNone(metric)
        self.assertTrue(len(metric.samples) > 0)

    def test_osdpl_glance_images_size(self):
        metric = self.get_metric("osdpl_glance_images_size")
        self.assertIsNotNone(metric)
        self.assertTrue(len(metric.samples) > 0)
