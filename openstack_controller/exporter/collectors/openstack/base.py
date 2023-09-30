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

from openstack_controller import utils
from openstack_controller.exporter.collectors import base
from openstack_controller import openstack_utils


LOG = utils.get_logger(__name__)


class OpenStackBaseMetricCollector(base.BaseMetricsCollector):
    # Service type to check for presence is catalog
    _os_service_types = []

    def __init__(self):
        super().__init__()
        self._oc = None

    @property
    def oc(self):
        if self._oc is None:
            try:
                self._oc = openstack_utils.OpenStackClientManager()
            except Exception as e:
                LOG.warning("Failed to initialize openstack client manager")
                LOG.exception(e)
        return self._oc

    @property
    def is_service_available(self):
        services = []
        cached_endpoints = []
        for service_type in self._os_service_types:
            # NOTE(vsaienko): endpoint_for returns list of endpoints from cache
            # during client initialization. identity.services returns actual
            # services from keystone catalog. If they do not mutch, service added
            # or removed. Reinitialize client to make sure we use updated catalog.
            cached_endpoints.append(self.oc.oc.endpoint_for(service_type))
            services.append(
                len(list(self.oc.oc.identity.services(type=service_type)))
            )
        if not any(services):
            LOG.info(f"Service not found for types {self._os_service_types}")
            return False
        else:
            if not any(cached_endpoints):
                LOG.info(
                    f"Catalog is changed for service types: {self._os_service_types}"
                )
                self._oc = None
                return False
        return True

    @property
    def can_collect_data(self):
        if self.oc is None:
            return False
        if not self.is_service_available:
            return False
        return True
