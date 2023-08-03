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


class OsdplGlanceMetricCollector(base.OpenStackBaseMetricCollector):
    _name = "osdpl_glance"
    _description = "OpenStack Image service metrics"
    _os_service_types = ["image"]

    def collect(self, osdpl):
        images = GaugeMetricFamily(
            f"{self._name}_images",
            "Number of glance images in environment",
            labels=["osdpl"],
        )
        if "images_total" in self.data:
            images.add_metric([osdpl.name], self.data["images_total"])

        images_size = GaugeMetricFamily(
            f"{self._name}_images_size",
            "Total size of all images in bytes",
            labels=["osdpl"],
        )
        if "images_size" in self.data:
            images_size.add_metric([osdpl.name], self.data["images_size"])

        yield images
        yield images_size

    def take_data(self):
        images_total = 0
        images_size = 0
        for image in self.oc.oc.image.images():
            images_total += 1
            images_size += image.get("size", 0)
        return {
            "images_total": images_total,
            "images_size": images_size,
        }
