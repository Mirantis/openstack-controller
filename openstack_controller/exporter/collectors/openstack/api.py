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

import requests
from urllib3.exceptions import InsecureRequestWarning

from prometheus_client.core import GaugeMetricFamily

from openstack_controller import utils
from openstack_controller.exporter.collectors.openstack import base


LOG = utils.get_logger(__name__)


class OsdplApiMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_api"
    _description = "OpenStack API endpoints"
    _os_service_types = ["identity"]

    def init_families(self):
        return {
            "status": GaugeMetricFamily(
                f"{self._name}_status",
                "API endpoint connection status",
                labels=["url", "service_type"],
            ),
            "latency": GaugeMetricFamily(
                f"{self._name}_latency",
                "API endpoint connection latency microseconds",
                labels=["url", "service_type"],
            ),
            "success": GaugeMetricFamily(
                f"{self._name}_success",
                "API endpoint connection success status",
                labels=["url", "service_type"],
            ),
        }

    def update_samples(self):
        statuses = []
        latencies = []
        successes = []
        for endpoint in self.oc.oc.identity.endpoints(interface="public"):
            service = self.oc.oc.identity.get_service(endpoint.service_id)
            service_type = self.oc.service_type_manager.get_service_type(
                service.type
            )
            if not service_type:
                LOG.warning(
                    f"Failed to get service_type for service {service}"
                )
                continue
            url = endpoint["url"].split("%")[0]
            success = True
            try:
                # TODO(vsaienko): mount ssl ca_cert from osdpl and use here.
                requests.packages.urllib3.disable_warnings(
                    category=InsecureRequestWarning
                )
                resp = requests.get(url, timeout=30, verify=False)
            except Exception as e:
                LOG.warning(f"Failed to get responce from {url}. Error: {e}")
                success = False
            if success:
                statuses.append(([url, service_type], resp.status_code))
                latencies.append(
                    ([url, service_type], resp.elapsed.microseconds)
                )
            successes.append(([url, service_type], int(success)))
        self.set_samples("status", statuses)
        self.set_samples("latency", latencies)
        self.set_samples("success", successes)
