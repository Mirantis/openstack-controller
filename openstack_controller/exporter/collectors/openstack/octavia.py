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


class OsdplOctaviaMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_octavia"
    _description = "OpenStack Orchestration service metrics"
    _os_service_types = ["load-balancer"]

    @cached_property
    def families(self):
        return {
            "loadbalancers": GaugeMetricFamily(
                f"{self._name}_loadbalancers",
                "Number of octavia loadbalancers in environment",
                labels=["osdpl", "operating_status", "privisioning_status"],
            ),
        }

    def update_samples(self):
        loadbalancers_by_status = {}
        for status in constants.LoadbalancerStatus:
            for p_status in constants.LoadbalancerProvisioningStatus:
                loadbalancers_by_status[(status.name, p_status.name)] = 0
        for lb in self.oc.oc.load_balancer.load_balancers():
            status = lb.get("operating_status")
            pr_status = lb.get("provisioning_status")
            if not hasattr(
                constants.LoadbalancerStatus, status
            ) or not hasattr(
                constants.LoadbalancerProvisioningStatus, pr_status
            ):
                LOG.warning(
                    f"Loadbalancer has unknown status ({status}, {pr_status})."
                )
                continue
            loadbalancers_by_status[(status, pr_status)] += 1
        loadbalancers_by_status_samples = []
        for labels, value in loadbalancers_by_status.items():
            loadbalancers_by_status_samples.append(
                ([self.osdpl.name, labels[0], labels[1]], value)
            )
        self.set_samples(
            "loadbalancers",
            loadbalancers_by_status_samples,
        )
