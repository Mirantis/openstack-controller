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

from prometheus_client.core import GaugeMetricFamily, InfoMetricFamily

from openstack_controller import utils
from openstack_controller.exporter.collectors.openstack import base
from openstack_controller.exporter import constants


LOG = utils.get_logger(__name__)


class OsdplNovaMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_nova"
    _description = "OpenStack Compute service metrics"
    _os_service_types = ["compute"]

    def __init__(self):
        super().__init__()
        self.hypervisor_resource_classes = ["vcpu", "disk_gb", "memory_mb"]
        self.hypervisor_metrics = ["used", "free", "allocation_ratio"]
        self.host_group_types = ["aggregate", "availability_zone"]
        self.cache = {}

    def update_cache(self):
        """Upadate cache for some API objects

        Cache only small amount of data from API that we use intensively in
        different places to avoid massive API calls. Should not add resources
        that consume a lot of space like servers.
        """

        self.cache["aggregates"] = list(self.oc.oc.compute.aggregates())
        self.cache["hypervisors"] = list(self.oc.oc.compute.hypervisors())
        self.cache["services"] = list(self.oc.oc.compute.services())
        self.cache["resource_providers"] = list(
            self.oc.oc.placement.resource_providers()
        )

    def get_host_resource_provider(self, name):
        for resource_provider in self.cache.get("resource_providers", []):
            if resource_provider["name"] == name:
                return resource_provider

    def get_resource_provider_inventories(self, rp):
        return self.oc.oc.placement.get(
            f"/resource_providers/{rp.id}/inventories"
        ).json()["inventories"]

    def get_resource_provider_usages(self, rp):
        return self.oc.oc.placement.get(
            f"/resource_providers/{rp.id}/usages"
        ).json()["usages"]

    def get_host_availability_zone(self, host):
        for service in self.cache.get("services", []):
            if service["host"] == host:
                return service["availability_zone"]

    def get_hosts_placement_metrics(self):
        """Return metrics from placement for hosts

        Takes into account only resource_classes we care about, specified in
        self.hypervisor_resource_classes
        """
        hosts = {}
        for hypervisor in self.cache.get("hypervisors", []):
            host_name = hypervisor["name"].split(".")[0]
            host = {}
            rp = self.get_host_resource_provider(hypervisor["name"])
            usages = self.get_resource_provider_usages(rp)
            inventories = self.get_resource_provider_inventories(rp)
            for k, used in usages.items():
                rc = k.lower()
                if rc not in self.hypervisor_resource_classes:
                    continue
                host[f"{rc}_used"] = used

            for k, inventory in inventories.items():
                rc = k.lower()
                if rc not in self.hypervisor_resource_classes:
                    continue
                host[rc] = inventory["total"] * inventory["allocation_ratio"]
                host[f"{rc}_allocation_ratio"] = inventory["allocation_ratio"]
                host[f"{rc}_free"] = (
                    inventory["total"] - inventory["reserved"]
                ) * inventory["allocation_ratio"] - host[f"{k.lower()}_used"]

            hosts[host_name] = host
        return hosts

    def summ_hosts_metrics(self, host_placement_metrics, hosts):
        res = {}
        for host in hosts:
            if host not in host_placement_metrics:
                continue
            host_metrics = host_placement_metrics[host]
            for metric, value in host_metrics.items():
                if "allocation_ratio" in metric:
                    continue
                res.setdefault(metric, 0)
                res[metric] += value
        return res

    @cached_property
    def families(self):
        res = {
            "service_state": GaugeMetricFamily(
                f"{self._name}_service_state",
                "Nova compute service state",
                labels=["host", "binary", "zone"],
            ),
            "service_status": GaugeMetricFamily(
                f"{self._name}_service_status",
                "Nova compute service status",
                labels=["host", "binary", "zone"],
            ),
            "instances": GaugeMetricFamily(
                f"{self._name}_instances",
                "Total number of instances",
                labels=[],
            ),
            "error_instances": GaugeMetricFamily(
                f"{self._name}_error_instances",
                "Total number of instances in error state",
                labels=[],
            ),
            "active_instances": GaugeMetricFamily(
                f"{self._name}_active_instances",
                "Total number of instances in active state",
                labels=[],
            ),
            "hypervisor_instances": GaugeMetricFamily(
                f"{self._name}_hypervisor_instances",
                "Total number of instances per hypervisor",
                labels=["host", "zone"],
            ),
            "aggregate_hosts": GaugeMetricFamily(
                f"{self._name}_aggregate_hosts",
                "Total number of compute hosts per host aggregate zone",
                labels=["id", "name"],
            ),
            "host_aggregate_info": InfoMetricFamily(
                f"{self._name}_host_aggregate",
                "Information about host aggregate mapping",
                labels=[],
            ),
            "availability_zone_info": InfoMetricFamily(
                f"{self._name}_availability_zone",
                "Information about nova availability zones",
                labels=[],
            ),
            "availability_zone_hosts": GaugeMetricFamily(
                f"{self._name}_availability_zone_hosts",
                "Total number of compute hosts per availability zone",
                labels=["zone"],
            ),
            "availability_zone_instances": GaugeMetricFamily(
                f"{self._name}_availability_zone_instances",
                "Total number of instances per availability zone.",
                labels=["zone"],
            ),
        }
        for resource_class in self.hypervisor_resource_classes:
            res[f"hypervisor_{resource_class}"] = GaugeMetricFamily(
                f"{self._name}_hypervisor_{resource_class}",
                f"Total number of total available {resource_class} on hypervisor",
                labels=["host", "zone"],
            )
            res[f"hypervisor_{resource_class}_used"] = GaugeMetricFamily(
                f"{self._name}_hypervisor_{resource_class}_used",
                f"Total number of used {resource_class} on hypervisor",
                labels=["host", "zone"],
            )
            res[f"hypervisor_{resource_class}_free"] = GaugeMetricFamily(
                f"{self._name}_hypervisor_{resource_class}_free",
                f"Total number of free {resource_class} on hypervisor",
                labels=["host", "zone"],
            )
            res[
                f"hypervisor_{resource_class}_allocation_ratio"
            ] = GaugeMetricFamily(
                f"{self._name}_hypervisor_{resource_class}_allocation_ratio",
                f"Total number of {resource_class} allocation_ratio on hypervisor",
                labels=["host", "zone"],
            )
        for group_type in self.host_group_types:
            for resource_class in self.hypervisor_resource_classes:
                res[f"{group_type}_{resource_class}"] = GaugeMetricFamily(
                    f"{self._name}_{group_type}_{resource_class}",
                    f"Total number of total available {resource_class} in {group_type}",
                    labels=["name"],
                )
                res[f"{group_type}_{resource_class}_used"] = GaugeMetricFamily(
                    f"{self._name}_{group_type}_{resource_class}_used",
                    f"Total number of used {resource_class} in {group_type}",
                    labels=["name"],
                )
                res[f"{group_type}_{resource_class}_free"] = GaugeMetricFamily(
                    f"{self._name}_{group_type}_{resource_class}_free",
                    f"Total number of free {resource_class} in {group_type}",
                    labels=["name"],
                )
        return res

    def update_host_group_samples(self, host_placement_metrics):
        """Update availability_zone and host aggregate samples.

        :param host_placement_metrics: Dictionary with placement metadata for hosts.
        """
        group_type_metrics = {"aggregate": {}, "availability_zone": {}}
        for aggregate in self.cache.get("aggregates", []):
            group_type = "aggregate"
            if aggregate.get("availability_zone") is not None:
                group_type = "availability_zone"

            metrics = self.summ_hosts_metrics(
                host_placement_metrics, aggregate["hosts"]
            )
            group_type_metrics[group_type][aggregate["name"]] = metrics

        group_type_metric_samples = {}
        for gt, gt_data in group_type_metrics.items():
            for gt_name, metrics in gt_data.items():
                for metric_name, metric_value in metrics.items():
                    group_type_metric_samples.setdefault(
                        f"{gt}_{metric_name}", []
                    )
                    group_type_metric_samples[f"{gt}_{metric_name}"].append(
                        ([gt_name], metric_value)
                    )

        for metric_name, samples in group_type_metric_samples.items():
            self.set_samples(metric_name, samples)

    def update_availability_zone_info_samples(self):
        availability_zone_info_samples = []
        for aggregate in self.cache.get("aggregates", []):
            if aggregate.get("availability_zone") is None:
                # This is regular aggregate
                continue
            availability_zone_info_samples.append(
                (
                    [],
                    {
                        "name": aggregate["name"],
                    },
                )
            )
        self.set_samples(
            "availability_zone_info", availability_zone_info_samples
        )

    def update_host_aggregate_samples(self):
        host_aggregate_info_samples = []
        host_aggregate_hosts_samples = []
        availability_zone_hosts_samples = []
        for aggregate in self.cache.get("aggregates", []):
            zone = aggregate.get("availability_zone")
            hosts = aggregate["hosts"] or []
            hosts_number = len(hosts)
            if zone:
                availability_zone_hosts_samples.append(([zone], hosts_number))
            else:
                aggregate_name = aggregate["name"]
                aggregate_id = aggregate["id"]
                for host in hosts:
                    host_aggregate_info_samples.append(
                        (
                            [],
                            {
                                "host": host,
                                "id": str(aggregate_id),
                                "name": aggregate_name,
                            },
                        )
                    )
                host_aggregate_hosts_samples.append(
                    (
                        [str(aggregate_id), aggregate_name],
                        hosts_number,
                    )
                )

        self.set_samples("host_aggregate_info", host_aggregate_info_samples)
        self.set_samples("aggregate_hosts", host_aggregate_hosts_samples)
        self.set_samples(
            "availability_zone_hosts", availability_zone_hosts_samples
        )

    def update_hypervisor_samples(self, host_placement_metrics):
        hypervisors_samples = {}
        for resource_class in self.hypervisor_resource_classes:
            hypervisors_samples[f"hypervisor_{resource_class}"] = []
            for metric in self.hypervisor_metrics:
                hypervisors_samples[
                    f"hypervisor_{resource_class}_{metric}"
                ] = []

        for host in host_placement_metrics:
            zone = self.get_host_availability_zone(host)
            for resource_class in self.hypervisor_resource_classes:
                host_metrics = host_placement_metrics[host]

                for metric_name, metric_value in host_metrics.items():
                    hypervisors_samples[f"hypervisor_{metric_name}"].append(
                        ([host, zone], metric_value)
                    )

        for metric_name, samples in hypervisors_samples.items():
            self.set_samples(metric_name, samples)

    def update_service_samples(self):
        state_samples = []
        status_samples = []
        for service in self.cache.get("services", {}):
            zone = service.get("availability_zone", "nova")
            state_samples.append(
                (
                    [
                        service["host"],
                        service["binary"],
                        zone,
                    ],
                    getattr(constants.ServiceState, service["state"]),
                )
            )
            status_samples.append(
                (
                    [
                        service["host"],
                        service["binary"],
                        zone,
                    ],
                    getattr(constants.ServiceStatus, service["status"]),
                )
            )

        self.set_samples("service_state", state_samples)
        self.set_samples("service_status", status_samples)

    def update_instances_samples(self):
        instances = {"total": 0, "active": 0, "error": 0}
        hypervisor_instances = {}
        availability_zone_instances_total = {}
        for instance in self.oc.oc.compute.servers(all_projects=True):
            status = instance["status"].lower()
            host = instance.get("compute_host")
            zone = instance.get("availability_zone")
            instances["total"] += 1
            if status in instances.keys():
                instances[status] += 1
                hypervisor_instances.setdefault(host, {"total": 0})
                hypervisor_instances[host]["total"] += 1
            if zone:
                availability_zone_instances_total.setdefault(zone, 0)
                availability_zone_instances_total[zone] += 1

        self.set_samples("instances", [([], instances["total"])])
        for key in ["error", "active"]:
            self.set_samples(f"{key}_instances", [([], instances[key])])

        availability_zone_instances_samples = []
        for zone, total in availability_zone_instances_total.items():
            availability_zone_instances_samples.append(([zone], total))
        self.set_samples(
            "availability_zone_instances", availability_zone_instances_samples
        )

        hypervisor_instances_samples = []
        for host, instance_number in hypervisor_instances.items():
            if host is None:
                continue
            hypervisor_instances_samples.append(
                (
                    [host, self.get_host_availability_zone(host) or "None"],
                    hypervisor_instances[host]["total"],
                )
            )
        self.set_samples("hypervisor_instances", hypervisor_instances_samples)

    def update_samples(self):
        self.update_cache()
        host_placement_metrics = self.get_hosts_placement_metrics()

        self.update_service_samples()
        self.update_hypervisor_samples(host_placement_metrics)
        self.update_host_aggregate_samples()
        self.update_host_group_samples(host_placement_metrics)
        self.update_availability_zone_info_samples()
        self.update_instances_samples()
