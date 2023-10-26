import os
import requests
import retry
import time
import logging

from prometheus_client.openmetrics.parser import text_string_to_metric_families

from openstack_controller import kube
from openstack_controller.tests.functional import config as conf
from openstack_controller.tests.functional import base

LOG = logging.getLogger(__name__)


class BaseFunctionalExporterTestCase(base.BaseFunctionalTestCase):
    known_metrics = {}
    # Dictionary with known metrics for exporter to check.
    #  * that metric is present
    #  * metric labels are set
    #  * metric has at least one sample
    #
    # {'<metric_name>': {"labels": []}}

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
    @retry.retry(
        requests.exceptions.ConnectionError,
        delay=1,
        tries=7,
        backoff=2,
        logger=LOG,
    )
    def metric_families(self):
        res = requests.get(self.exporter_url, timeout=60)
        return text_string_to_metric_families(res.text + "# EOF")

    def get_metric(self, name, metric_families=None):
        metric_families = metric_families or self.metric_families
        for metric in metric_families:
            if metric.name == name:
                LOG.info(f"Got metric: {metric}")
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

    def get_metric_after_refresh(self, metric_name, scrape_collector):
        current_time = time.time()
        all_metrics = list(self.metric_families)
        scrape_collector_metrics = self.get_metric(
            "osdpl_scrape_collector_start_timestamp", all_metrics
        )
        start_time = self.filter_metric_samples(
            scrape_collector_metrics, {"collector": scrape_collector}
        )
        while True:
            if start_time[0].value >= current_time:
                LOG.debug(
                    f"Metrics for collector {scrape_collector} were refreshed in exporter after updates in openstack API."
                )
                return self.get_metric(metric_name, all_metrics)
            time.sleep(conf.METRIC_INTERVAL_TIMEOUT)
            timed_out = (
                int(time.time()) - int(current_time) >= conf.METRIC_TIMEOUT
            )
            message = f"Metrics for collector {scrape_collector} were not updated after timeout {conf.METRIC_TIMEOUT}."
            if timed_out:
                logging.error(message)
                raise TimeoutError(message)
            all_metrics = list(self.metric_families)
            scrape_collector_metrics = self.get_metric(
                "osdpl_scrape_collector_start_timestamp", all_metrics
            )
            start_time = self.filter_metric_samples(
                scrape_collector_metrics, {"collector": scrape_collector}
            )

    def test_known_metrics_present_and_not_none(self):
        for metric_name in self.known_metrics.keys():
            metric = self.get_metric(metric_name)
            self.assertIsNotNone(metric)
            self.assertTrue(len(metric.samples) > 0)

    def test_known_metrics_labels(self):
        for metric_name, data in self.known_metrics.items():
            metric = self.get_metric(metric_name)
            for sample in metric.samples:
                for label in data.get("labels", []):
                    self.assertTrue(label in sample.labels)
