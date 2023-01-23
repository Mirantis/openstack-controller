#!/usr/bin/env python3
#    Copyright 2023 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import yaml
import base64

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from prometheus_client.core import GaugeMetricFamily

from openstack_controller import kube, utils
from openstack_controller.exporter import settings
from openstack_controller.exporter.collectors import base


LOG = utils.get_logger(__name__)


class OsdplCertsMetricCollector(base.BaseMetricsCollector):
    _name = "osdpl_certificate"
    _description = "Info about OpenStack certificates"

    def __init__(self):
        super().__init__()
        with open(settings.OSCTL_EXPORTER_CERTIFICATES_INFO_FILE) as f:
            self.certs_info = yaml.safe_load(f)
        self.data = {}

    @property
    def can_collect_data(self):
        return True

    def collect(self, osdpl):
        gauge = GaugeMetricFamily(
            f"{self._name}_expiry",
            f"{self._description}: expiration unix timestamp",
            labels=["identifier", "osdpl"],
        )
        for identifier, cert in self.data.items():
            gauge.add_metric(
                [identifier, osdpl.name],
                float(cert.not_valid_after.timestamp()),
            )
        yield gauge

    def take_data(self):
        return self.load_certificates()

    def load_certificates(self):
        """Load certificates from kubernetes secrets

        Return dictionary with certificate information from certificates
        stored in kubernetes secrets:

        :param certs_info: Dictionary with certs info.
                           {
                                "<identifier>": {
                                    "name": "<name of secret>",
                                    "namespace": "<namespace>",
                                    "key_name": "<name of key with certificate>"
                                }
                            }
        :returns : Dictionary with cert identifier and certs objects
        """
        LOG.info(f"Loading certificates: {self.certs_info}")
        res = {}
        for identifier, data in self.certs_info.items():
            secret = kube.find(kube.Secret, data["name"], data["namespace"])
            if not secret:
                LOG.error(f"Specified secret {data['name']} is not found.")
            cert_content = secret.obj["data"].get(data["key_name"])
            if not cert_content:
                LOG.error(
                    f"Specified data['key_name'] not found in secret data['name']"
                )
            cert_content = base64.b64decode(cert_content)
            cert = x509.load_pem_x509_certificate(
                cert_content, default_backend()
            )
            res[identifier] = cert
        return res
