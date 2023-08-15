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


LOG = utils.get_logger(__name__)


class OsdplNeutronMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_neutron"
    _description = "OpenStack Networking service metrics"
    _os_service_types = ["network"]

    @cached_property
    def families(self):
        return {
            "networks": GaugeMetricFamily(
                f"{self._name}_networks",
                "Number of neutron networks in environment",
                labels=["osdpl"],
            ),
            "subnets": GaugeMetricFamily(
                f"{self._name}_subnets",
                "Number of neutron subnets in environment",
                labels=["osdpl"],
            ),
            "ports": GaugeMetricFamily(
                f"{self._name}_ports",
                "Number of neutron ports in environment",
                labels=["osdpl"],
            ),
            "routers": GaugeMetricFamily(
                f"{self._name}_routers",
                "Number of neutron routers in environment",
                labels=["osdpl"],
            ),
            "floating_ips": GaugeMetricFamily(
                f"{self._name}_floating_ips",
                "Number of neutron floating ips in environment",
                labels=["osdpl", "state"],
            ),
            "agent_state": GaugeMetricFamily(
                f"{self._name}_agent_state",
                "State of neutron agent in environment",
                labels=["host", "binary", "osdpl", "zone"],
            ),
            "agent_status": GaugeMetricFamily(
                f"{self._name}_agent_status",
                "Administrative status of neutron agent in environment",
                labels=["host", "binary", "osdpl", "zone"],
            ),
        }

    def update_samples(self):
        for resource in ["networks", "subnets", "ports", "routers"]:
            total = len(list(getattr(self.oc.oc.network, resource)()))
            self.set_samples(resource, [([self.osdpl.name], total)])

        floating_ips_associated = 0
        floating_ips_not_associated = 0
        for fip in self.oc.oc.network.ips():
            if fip.get("port_id") is not None:
                floating_ips_associated += 1
            else:
                floating_ips_not_associated += 1

        self.set_samples(
            "floating_ips",
            [
                ([self.osdpl.name, "associated"], floating_ips_associated),
                (
                    [self.osdpl.name, "not_associated"],
                    floating_ips_not_associated,
                ),
            ],
        )

        agent_samples = {"is_alive": [], "is_admin_state_up": []}
        for agent in self.oc.oc.network.agents():
            az = agent["availability_zone"] or "nova"
            for field in agent_samples.keys():
                if field in agent.to_dict():
                    agent_samples[field].append(
                        (
                            [
                                agent["host"],
                                agent["binary"],
                                self.osdpl.name,
                                az,
                            ],
                            int(agent[field]),
                        )
                    )
        self.set_samples("agent_state", agent_samples["is_alive"])
        self.set_samples("agent_status", agent_samples["is_admin_state_up"])
