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
            "instances": GaugeMetricFamily(
                f"{self._name}_instances",
                "Total number of instances",
                labels=["osdpl"],
            ),
            "error_instances": GaugeMetricFamily(
                f"{self._name}_error_instances",
                "Total number of instances in error state",
                labels=["osdpl"],
            ),
            "active_instances": GaugeMetricFamily(
                f"{self._name}_active_instances",
                "Total number of instances in active state",
                labels=["osdpl"],
            ),
            "hypervisor_instances": GaugeMetricFamily(
                f"{self._name}_hypervisor_instances",
                "Total number of instances per hypervisor",
                labels=["host", "zone", "osdpl"],
            ),
        }

    def update_samples(self):
        state_samples = []
        status_samples = []
        hypervisors_info = {}

        for service in self.oc.compute_get_services():
            zone = service.get("availability_zone", "nova")
            hypervisors_info[service["host"]] = {
                "zone": service["availability_zone"]
            }
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

        instances = {"total": 0, "active": 0, "error": 0}
        hypervisor_instances = {}
        for instance in self.oc.oc.compute.servers(all_projects=True):
            status = instance["status"].lower()
            host = instance.get("compute_host")
            instances["total"] += 1
            if status in instances.keys():
                instances[status] += 1
            if host is not None:
                hypervisor_instances.setdefault(host, {"total": 0})
                hypervisor_instances[host]["total"] += 1

        self.set_samples(
            "instances", [([self.osdpl.name], instances["total"])]
        )
        for key in ["error", "active"]:
            self.set_samples(
                f"{key}_instances", [([self.osdpl.name], instances[key])]
            )
        hypervisor_instances_samples = []
        for host, instance_number in hypervisor_instances.items():
            hypervisor_instances_samples.append(
                (
                    [
                        host,
                        hypervisors_info.get(host, {}).get("zone", "None"),
                        self.osdpl.name,
                    ],
                    hypervisor_instances[host]["total"],
                )
            )
        self.set_samples("hypervisor_instances", hypervisor_instances_samples)
