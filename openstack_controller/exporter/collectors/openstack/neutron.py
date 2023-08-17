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
                labels=[],
            ),
            "subnets": GaugeMetricFamily(
                f"{self._name}_subnets",
                "Number of neutron subnets in environment",
                labels=[],
            ),
            "ports": GaugeMetricFamily(
                f"{self._name}_ports",
                "Number of neutron ports in environment",
                labels=[],
            ),
            "error_ports": GaugeMetricFamily(
                f"{self._name}_error_ports",
                "Number of neutron ports in the ERROR state in environment",
                labels=[],
            ),
            "down_ports": GaugeMetricFamily(
                f"{self._name}_down_ports",
                "Number of neutron ports in the DOWN state in environment",
                labels=[],
            ),
            "active_ports": GaugeMetricFamily(
                f"{self._name}_active_ports",
                "Number of neutron ports in the ACTIVE state in environment",
                labels=[],
            ),
            "routers": GaugeMetricFamily(
                f"{self._name}_routers",
                "Number of neutron routers in environment",
                labels=[],
            ),
            "floating_ips": GaugeMetricFamily(
                f"{self._name}_floating_ips",
                "Number of neutron floating ips in environment",
                labels=["state"],
            ),
            "agent_state": GaugeMetricFamily(
                f"{self._name}_agent_state",
                "State of neutron agent in environment",
                labels=["host", "binary", "zone"],
            ),
            "agent_status": GaugeMetricFamily(
                f"{self._name}_agent_status",
                "Administrative status of neutron agent in environment",
                labels=["host", "binary", "zone"],
            ),
        }

    def update_samples(self):
        for resource in ["networks", "subnets", "routers"]:
            total = len(list(getattr(self.oc.oc.network, resource)()))
            self.set_samples(resource, [([], total)])

        ports = {"total": 0, "active": 0, "down": 0}
        for port in self.oc.oc.network.ports():
            port_status = port["status"].lower()
            if port_status in ports.keys():
                ports[port_status] += 1

        self.set_samples("ports", [([], ports["total"])])
        for port_status in ["active", "down"]:
            self.set_samples(
                f"{port_status}_ports",
                [([], ports[port_status])],
            )

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
                (["associated"], floating_ips_associated),
                (
                    ["not_associated"],
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
                                az,
                            ],
                            int(agent[field]),
                        )
                    )
        self.set_samples("agent_state", agent_samples["is_alive"])
        self.set_samples("agent_status", agent_samples["is_admin_state_up"])
