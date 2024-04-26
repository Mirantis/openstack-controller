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


class OsdplMasakariMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_masakari"
    _description = "OpenStack Instance HA service metrics"
    _os_service_types = ["instance-ha", "ha"]

    @utils.timeit
    def init_families(self):
        return {
            "segments": GaugeMetricFamily(
                f"{self._name}_segments",
                "Number of segments in the environment",
                labels=[],
            ),
            "segment_hosts": GaugeMetricFamily(
                f"{self._name}_segment_hosts",
                "Number of hosts in specific segment in the environment",
                labels=["segment"],
            ),
        }

    @utils.timeit
    def update_samples(self):
        segments_total = 0
        segment_hosts_samples = []
        for segment in self.oc.oc.ha.segments():
            segment_uuid = segment["uuid"]
            segment_name = segment["name"]
            segments_total += 1
            segment_hosts = len(list(self.oc.oc.ha.hosts(segment_uuid)))
            segment_hosts_samples.append(
                (
                    [
                        segment_name,
                    ],
                    segment_hosts,
                )
            )
        self.set_samples("segments", [([], segments_total)])
        self.set_samples("segment_hosts", segment_hosts_samples)
