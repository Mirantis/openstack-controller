import requests

from unittest import TestCase
from prometheus_client.openmetrics.parser import text_string_to_metric_families

from openstack_controller import kube
from openstack_controller import openstack_utils


class BaseFunctionalTestCase(TestCase):
    def setUp(self):
        self.exporter_url = self.get_exporter_url()
        self.metric_families = [x for x in self.get_metric_families()]
        self.kube_api = kube.kube_client()
        self.ocm = openstack_utils.OpenStackClientManager()
        self.osdpl = kube.get_osdpl()

    def get_exporter_url(self):
        svc_class = kube.get_object_by_kind("Service")
        svc = kube.find(
            svc_class, "openstack-controller-exporter", namespace="osh-system"
        )
        internal_ip = svc.obj["spec"]["clusterIPs"][0]
        return f"http://{internal_ip}:9102"

    def get_metric_families(self):
        res = requests.get(self.exporter_url)
        return text_string_to_metric_families(res.text + "# EOF")

    def get_metric(self, name):
        for metric in self.metric_families:
            if metric.name == name:
                return metric

    def filter_metric_samples(self, metric, labels):
        res = []
        for sample in metric.samples:
            for label, value in labels.items():
                if sample.labels.get(label) != value:
                    break
            else:
                res.append(sample)
        return res
