import os
import requests

from prometheus_client.openmetrics.parser import text_string_to_metric_families

from openstack_controller import kube
from openstack_controller.tests.functional import base


class BaseFunctionalExporterTestCase(base.BaseFunctionalTestCase):
    def setUp(self):
        super().setUp()
        self.exporter_url = self.get_exporter_url()

    def get_exporter_url(self):
        if os.environ.get("OSDPL_EXPORTER_URL"):
            return os.environ.get("OSDPL_EXPORTER_URL")
        svc_class = kube.get_object_by_kind("Service")
        svc = kube.find(
            svc_class, "openstack-controller-exporter", namespace="osh-system"
        )
        internal_ip = svc.obj["spec"]["clusterIPs"][0]
        return f"http://{internal_ip}:9102"

    @property
    def metric_families(self):
        res = requests.get(self.exporter_url, timeout=60)
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
