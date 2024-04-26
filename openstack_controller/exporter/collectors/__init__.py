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

from openstack_controller.exporter.collectors import base
from openstack_controller.exporter.collectors.base import OsdplMetricsCollector

from openstack_controller.exporter.collectors.certificates import (
    OsdplCertsMetricCollector,
)
from openstack_controller.exporter.collectors.credentials import (
    OsdplCredentialsMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.nova import (
    OsdplNovaMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.ironic import (
    OsdplIronicMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.heat import (
    OsdplHeatMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.keystone import (
    OsdplKeystoneMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.glance import (
    OsdplGlanceMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.cinder import (
    OsdplCinderMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.neutron import (
    OsdplNeutronMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.octavia import (
    OsdplOctaviaMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.aodh import (
    OsdplAodhMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.api import (
    OsdplApiMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.manila import (
    OsdplManilaMetricCollector,
)

from openstack_controller.exporter.collectors.osdpl import (
    OsdplMetricCollector,
)
from openstack_controller.exporter.collectors.openstack.masakari import (
    OsdplMasakariMetricCollector,
)

__all__ = (
    OsdplMetricsCollector,
    OsdplCertsMetricCollector,
    OsdplCredentialsMetricCollector,
    OsdplNovaMetricCollector,
    OsdplIronicMetricCollector,
    OsdplMetricCollector,
    OsdplHeatMetricCollector,
    OsdplKeystoneMetricCollector,
    OsdplGlanceMetricCollector,
    OsdplCinderMetricCollector,
    OsdplNeutronMetricCollector,
    OsdplOctaviaMetricCollector,
    OsdplAodhMetricCollector,
    OsdplApiMetricCollector,
    OsdplManilaMetricCollector,
    OsdplMasakariMetricCollector,
)

registry = base.BaseMetricsCollector.registry
