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


class OsdplAodhMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_aodh"
    _description = "OpenStack Orchestration service metrics"
    _os_service_types = ["alarm", "alarming"]

    @cached_property
    def families(self):
        return {
            "alarms": GaugeMetricFamily(
                f"{self._name}_alarms",
                "Number of aodh alarms in environment",
                labels=[],
            )
        }

    def update_samples(self):
        alarms = self.oc.oc.alarm.get("/alarms").json()
        self.set_samples("alarms", [([], len(alarms))])