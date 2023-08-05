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
from openstack_controller.exporter import constants


LOG = utils.get_logger(__name__)


class OsdplCinderMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_cinder"
    _description = "OpenStack Volume service metrics"
    _os_service_types = [
        "block-storage",
        "volumev3",
        "volumev2",
        "volume",
        "block-store",
    ]

    def collect(self, osdpl):
        volumes = GaugeMetricFamily(
            f"{self._name}_volumes",
            "Number of cinder volumes in environment",
            labels=["osdpl"],
        )
        if "volumes_total" in self.data:
            volumes.add_metric([osdpl.name], self.data["volumes_total"])

        volumes_size = GaugeMetricFamily(
            f"{self._name}_volumes_size",
            "Total size of all volumes in bytes",
            labels=["osdpl"],
        )
        if "volumes_size" in self.data:
            volumes_size.add_metric([osdpl.name], self.data["volumes_size"])

        snapshots = GaugeMetricFamily(
            f"{self._name}_snapshots",
            "Number of cinder snapshots in environment",
            labels=["osdpl"],
        )
        if "snapshots_total" in self.data:
            snapshots.add_metric([osdpl.name], self.data["snapshots_total"])

        snapshots_size = GaugeMetricFamily(
            f"{self._name}_snapshots_size",
            "Total size of all snapshots in bytes",
            labels=["osdpl"],
        )
        if "snapshots_size" in self.data:
            snapshots_size.add_metric(
                [osdpl.name], self.data["snapshots_size"]
            )

        yield volumes
        yield volumes_size
        yield snapshots
        yield snapshots_size

    def take_data(self):
        volumes_total = 0
        volumes_size = 0
        snapshots_total = 0
        snapshots_size = 0
        for volume in self.oc.oc.volume.volumes(all_tenants=True):
            volumes_total += 1
            # NOTE(vsaienko): the size may be None from API.
            volumes_size += volume.get("size") or 0

        for snapshot in self.oc.oc.volume.snapshots(all_tenants=True):
            snapshots_total += 1
            snapshots_size += snapshot.get("size") or 0

        return {
            "volumes_total": volumes_total,
            "volumes_size": volumes_size * constants.Gi,
            "snapshots_total": snapshots_total,
            "snapshots_size": snapshots_size * constants.Gi,
        }
