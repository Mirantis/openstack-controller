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

from functools import cached_property

from prometheus_client.core import GaugeMetricFamily

from openstack_controller import utils
from openstack_controller.exporter.collectors.openstack import base
from openstack_controller.exporter import constants


LOG = utils.get_logger(__name__)


class OsdplNovaMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_nova"
    _description = "OpenStack Compute service metrics"
    _os_service_types = ["compute"]

    @cached_property
    def families(self):
        return {
            "service_state": GaugeMetricFamily(
                f"{self._name}_service_state",
                "Nova compute service state",
                labels=["host", "binary", "zone", "osdpl"],
            ),
            "service_status": GaugeMetricFamily(
                f"{self._name}_service_status",
                "Nova compute service status",
                labels=["host", "binary", "zone", "osdpl"],
            ),
        }

    def update_samples(self):
        state_samples = []
        status_samples = []
        for service in self.oc.compute_get_services():
            zone = service.get("availability_zone", "nova")
            state_samples.append(
                (
                    [
                        service["host"],
                        service["binary"],
                        zone,
                        self.osdpl.name,
                    ],
                    getattr(constants.ServiceState, service["state"]),
                )
            )
            status_samples.append(
                (
                    [
                        service["host"],
                        service["binary"],
                        zone,
                        self.osdpl.name,
                    ],
                    getattr(constants.ServiceStatus, service["status"]),
                )
            )
            self.set_samples("service_state", state_samples)
            self.set_samples("service_status", status_samples)
