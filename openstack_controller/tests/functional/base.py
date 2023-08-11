from unittest import TestCase

from openstack_controller import kube
from openstack_controller import openstack_utils


class BaseFunctionalTestCase(TestCase):
    def setUp(self):
        self.kube_api = kube.kube_client()
        self.ocm = openstack_utils.OpenStackClientManager()
        self.osdpl = kube.get_osdpl()
