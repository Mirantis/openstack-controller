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

    @cached_property
    def families(self):
        return {
            "volumes": GaugeMetricFamily(
                f"{self._name}_volumes",
                "Number of cinder volumes in environment",
                labels=["osdpl"],
            ),
            "volumes_size": GaugeMetricFamily(
                f"{self._name}_volumes_size",
                "Total size of all volumes in bytes",
                labels=["osdpl"],
            ),
            "snapshots": GaugeMetricFamily(
                f"{self._name}_snapshots",
                "Number of cinder snapshots in environment",
                labels=["osdpl"],
            ),
            "snapshots_size": GaugeMetricFamily(
                f"{self._name}_snapshots_size",
                "Total size of all snapshots in bytes",
                labels=["osdpl"],
            ),
            "service_state": GaugeMetricFamily(
                f"{self._name}_service_state",
                "Cinder service state",
                labels=["host", "binary", "zone", "osdpl"],
            ),
            "service_status": GaugeMetricFamily(
                f"{self._name}_service_status",
                "Cinder service status",
                labels=["host", "binary", "zone", "osdpl"],
            ),
            "pool_free_capacity": GaugeMetricFamily(
                f"{self._name}_pool_free_capacity",
                "Free capacity in bytes of cinder backend pools in environment",
                labels=["osdpl", "name"],
            ),
            "pool_total_capacity": GaugeMetricFamily(
                f"{self._name}_pool_total_capacity",
                "Total capacity in bytes of cinder backend pools in environment",
                labels=["osdpl", "name"],
            ),
            "pool_allocated_capacity": GaugeMetricFamily(
                f"{self._name}_pool_allocated_capacity",
                "Allocated capacity in bytes of cinder backend pools in environment",
                labels=["osdpl", "name"],
            ),
        }

    def update_samples(self):
        volumes_total = 0
        volumes_size = 0
        snapshots_total = 0
        snapshots_size = 0
        for volume in self.oc.oc.volume.volumes(all_tenants=True):
            volumes_total += 1
            # NOTE(vsaienko): the size may be None from API.
            volumes_size += volume.get("size") or 0
        self.set_samples("volumes", [([self.osdpl.name], volumes_total)])
        self.set_samples(
            "volumes_size", [([self.osdpl.name], volumes_size * constants.Gi)]
        )
        for snapshot in self.oc.oc.volume.snapshots(all_tenants=True):
            snapshots_total += 1
            snapshots_size += snapshot.get("size") or 0
        self.set_samples("snapshots", [([self.osdpl.name], snapshots_total)])
        self.set_samples(
            "snapshots_size",
            [([self.osdpl.name], snapshots_size * constants.Gi)],
        )

        service_state_samples = []
        service_status_samples = []
        for service in self.oc.volume_get_services():
            service_state_samples.append(
                (
                    [
                        service["host"],
                        service["binary"],
                        service["zone"],
                        self.osdpl.name,
                    ],
                    getattr(constants.ServiceState, service["state"]),
                )
            )
            service_status_samples.append(
                (
                    [
                        service["host"],
                        service["binary"],
                        service["zone"],
                        self.osdpl.name,
                    ],
                    getattr(constants.ServiceStatus, service["status"]),
                )
            )
        self.set_samples("service_state", service_state_samples)
        self.set_samples("service_status", service_status_samples)

        pool_free_capacity_samples = []
        pool_total_capacity_samples = []
        pool_allocated_capacity_samples = []
        for backend_pool in self.oc.oc.volume.backend_pools():
            pool_free_capacity_samples.append(
                (
                    [self.osdpl.name, backend_pool["name"]],
                    (
                        backend_pool.get("capabilities", {}).get(
                            "free_capacity_gb"
                        )
                        or 0
                    )
                    * constants.Gi,
                )
            )
            pool_total_capacity_samples.append(
                (
                    [self.osdpl.name, backend_pool["name"]],
                    (
                        backend_pool.get("capabilities", {}).get(
                            "total_capacity_gb"
                        )
                        or 0
                    )
                    * constants.Gi,
                )
            )
            pool_allocated_capacity_samples.append(
                (
                    [self.osdpl.name, backend_pool["name"]],
                    (
                        backend_pool.get("capabilities", {}).get(
                            "allocated_capacity_gb"
                        )
                        or 0
                    )
                    * constants.Gi,
                )
            )

        self.set_samples("pool_free_capacity", pool_free_capacity_samples)
        self.set_samples("pool_total_capacity", pool_total_capacity_samples)
        self.set_samples(
            "pool_allocated_capacity", pool_allocated_capacity_samples
        )