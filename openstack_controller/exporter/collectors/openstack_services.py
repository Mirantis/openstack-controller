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

from prometheus_client.core import StateSetMetricFamily, GaugeMetricFamily

from openstack_controller import utils
from openstack_controller.exporter.collectors import base
from openstack_controller import openstack_utils


LOG = utils.get_logger(__name__)

OPENSTACK_CLIENT = None


def get_os_client():
    global OPENSTACK_CLIENT
    if OPENSTACK_CLIENT is None:
        OPENSTACK_CLIENT = openstack_utils.OpenStackClientManager()
    return OPENSTACK_CLIENT


class OpenStackBaseMetricCollector(base.BaseMetricsCollector):
    # Service type to check for presence is catalog
    _os_service_types = []

    def __init__(self):
        super().__init__()

    @property
    def oc(self):
        try:
            return get_os_client()
        except Exception as e:
            LOG.warning("Failed to initialize openstack client manager")
            LOG.exception(e)

    @property
    def is_service_available(self):
        for service_type in self._os_service_types:
            if self.oc.oc.endpoint_for(service_type):
                return True
        LOG.info(
            f"Can't find endpoints for service types {self._os_service_types}"
        )

    @property
    def can_collect_data(self):
        if self.oc is None:
            return False
        if not self.is_service_available:
            return False
        return True


class OsdplNovaMetricCollector(OpenStackBaseMetricCollector):
    _name = "osdpl_nova"
    _description = "OpenStack Compute service metrics"
    _os_service_types = ["compute"]

    def collect(self, osdpl):
        state_metric = StateSetMetricFamily(
            f"{self._name}_service_state",
            "Nova compute service state",
            labels=["host", "binary", "osdpl"],
        )
        status_metric = StateSetMetricFamily(
            f"{self._name}_service_status",
            "Nova compute service status",
            labels=["host", "binary", "osdpl"],
        )

        for service in self.data.get("services", []):
            is_up = service["state"] == "up"
            is_enabled = service["status"] == "enabled"
            state_metric.add_metric(
                [service["host"], service["binary"], osdpl.name],
                {"up": is_up, "down": not is_up},
            )
            status_metric.add_metric(
                [service["host"], service["binary"], osdpl.name],
                {"enabled": is_enabled, "disabled": not is_enabled},
            )

        yield state_metric
        yield status_metric

    def take_data(self):
        return {"services": [x for x in self.oc.compute_get_services()]}


class OsdplIronicMetricCollector(OpenStackBaseMetricCollector):
    _name = "osdpl_ironic"
    _description = "OpenStack Baremetal service metrics"
    _os_service_types = ["baremetal"]

    def collect(self, osdpl):
        nodes_total = GaugeMetricFamily(
            f"{self._name}_nodes_total",
            "The baremetal nodes total count",
            labels=["osdpl"],
        )
        nodes_available = StateSetMetricFamily(
            f"{self._name}_nodes_available",
            "Available baremetal nodes",
            labels=["uuid", "name", "osdpl"],
        )
        total_nodes = 0
        for node in self.data.get("nodes", {}):
            total_nodes = 1 + total_nodes
            is_available = self.oc.baremetal_is_node_available(node)
            # TODO(vsaienko): use uuid when switch to zed version
            nodes_available.add_metric(
                [node["id"], node["name"], osdpl.name],
                {"available": is_available},
            )
        nodes_total.add_metric([osdpl.name], total_nodes)

        yield nodes_available
        yield nodes_total

    def take_data(self):
        return {"nodes": [x for x in self.oc.baremetal_get_nodes()]}
