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


class OsdplKeystoneMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_keystone"
    _description = "OpenStack Identity service metrics"
    _os_service_types = ["identity"]

    @cached_property
    def families(self):
        return {
            "users": GaugeMetricFamily(
                f"{self._name}_users",
                "Number of keystone users in environment",
                labels=["osdpl"],
            ),
            "domains": GaugeMetricFamily(
                f"{self._name}_domains",
                "Number of keystone domains in environment",
                labels=["osdpl"],
            ),
            "projects": GaugeMetricFamily(
                f"{self._name}_projects",
                "Number of keystone projects in environment",
                labels=["osdpl"],
            ),
        }

    def users_total(self, domain_id):
        users_total = 0
        for user in self.oc.oc.identity.users(domain_id=domain_id):
            users_total += 1
        return users_total

    def projects_total(self, domain_id):
        projects_total = 0
        for project in self.oc.oc.identity.projects(domain_id=domain_id):
            projects_total += 1
        return projects_total

    def update_samples(self):
        domains_total = 0
        users_total = 0
        projects_total = 0
        for domain in self.oc.oc.identity.domains():
            domains_total += 1
            users_total += self.users_total(domain["id"])
            projects_total += self.projects_total(domain["id"])
        self.set_samples("users", [([self.osdpl.name], users_total)])
        self.set_samples("projects", [([self.osdpl.name], projects_total)])
        self.set_samples("domains", [([self.osdpl.name], domains_total)])