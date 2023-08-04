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

from prometheus_client.core import GaugeMetricFamily

from openstack_controller import utils
from openstack_controller.exporter.collectors.openstack import base


LOG = utils.get_logger(__name__)


class OsdplIronicMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_ironic"
    _description = "OpenStack Baremetal service metrics"
    _os_service_types = ["baremetal"]

    def collect(self, osdpl):
        nodes_total = GaugeMetricFamily(
            f"{self._name}_nodes_total",
            "The baremetal nodes total count",
            labels=["osdpl"],
        )
        if "nodes_total" in self.data:
            nodes_total.add_metric([osdpl.name], self.data["nodes_total"])

        yield nodes_total

    def take_data(self):
        return {"nodes_total": len([x for x in self.oc.baremetal_get_nodes()])}
