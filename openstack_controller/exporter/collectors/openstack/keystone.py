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


class OsdplKeystoneMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_keystone"
    _description = "OpenStack Identity service metrics"
    _os_service_types = ["identity"]

    def collect(self, osdpl):
        users = GaugeMetricFamily(
            f"{self._name}_users",
            "Number of keystone users in environment",
            labels=["osdpl"],
        )
        if "users_total" in self.data:
            users.add_metric([osdpl.name], self.data["users_total"])

        domains = GaugeMetricFamily(
            f"{self._name}_domains",
            "Number of keystone domains in environment",
            labels=["osdpl"],
        )
        if "domains_total" in self.data:
            domains.add_metric([osdpl.name], self.data["domains_total"])

        projects = GaugeMetricFamily(
            f"{self._name}_project",
            "Number of keystone projects in environment",
            labels=["osdpl"],
        )
        if "projects_total" in self.data:
            projects.add_metric([osdpl.name], self.data["projects_total"])

        yield users
        yield projects
        yield domains

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

    def take_data(self):
        domains_total = 0
        users_total = 0
        projects_total = 0
        for domain in self.oc.oc.identity.domains():
            domains_total += 1
            users_total += self.users_total(domain["id"])
            projects_total += self.projects_total(domain["id"])
        return {
            "users_total": users_total,
            "projects_total": projects_total,
            "domains_total": domains_total,
        }
