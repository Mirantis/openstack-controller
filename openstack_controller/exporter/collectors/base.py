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


import abc
from datetime import datetime
import sys
from threading import Thread

from openstack_controller.exporter import settings
from openstack_controller.exporter import collectors
from openstack_controller import utils
from openstack_controller import kube


LOG = utils.get_logger(__name__)


class OsdplMetricsCollector(object):
    def __init__(self):
        self.collector_instances = []
        self.gather_tasks = {}
        self.max_poll_timeout = settings.OSCTL_EXPORTER_MAX_POLL_TIMEOUT

        for name, collector in collectors.registry.items():
            if name in settings.OSCTL_EXPORTER_ENABLED_COLLECTORS:
                LOG.info(f"Adding collector {name} to registry")
                instance = collector()
                self.collector_instances.append(instance)

    def submit_task(self, name, func):
        """Submit a taks with data collection

        :param name: The name of task to start
        :param func: function to run in tread
        :return: False if task is already running, True otherwise.
        """
        start = datetime.utcnow()
        if name in self.gather_tasks:
            running_for = start - self.gather_tasks[name]["started_at"]
            LOG.warning(
                f"The task {name} already running for {running_for}. Highly likely this occur due to frequent metric collection."
            )
            return False
        LOG.info(f"Starting metric collector thread  for {name}")
        future = Thread(target=func)
        self.gather_tasks[name] = {"future": future, "started_at": start}
        future.start()
        return True

    def complete_task(self, name):
        self.gather_tasks.pop(name)

    def check_stuck_tasks(self):
        for name, task in self.gather_tasks.copy().items():
            if (
                datetime.utcnow() - task["started_at"]
            ).total_seconds() > self.max_poll_timeout:
                LOG.error(
                    f"Task {name} stuck for more than {self.max_poll_timeout}."
                )
                sys.exit(1)

    def update_tasks_status(self):
        for name, task in self.gather_tasks.copy().items():
            future = task["future"]
            if not future.is_alive():
                took_time = datetime.utcnow() - task["started_at"]
                self.complete_task(name)
                LOG.info(f"Task {name} took {took_time} to complete.")
        self.check_stuck_tasks()

    def collect(self):
        osdpl = kube.get_osdpl()

        self.update_tasks_status()
        if osdpl:
            LOG.info(f"The osdpl {osdpl.name} found. Collecting metrics")
            for collector_instance in self.collector_instances:
                self.submit_task(
                    collector_instance._name, collector_instance.refresh_data
                )

        for collector_instance in self.collector_instances:
            yield from collector_instance.collect(osdpl)


class BaseMetricsCollector(object):
    _name = "osdpl_metric_name"
    _description = "osdpl metric description"
    registry = {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        cls.registry[cls._name] = cls

    def __init__(self):
        self.data = {}

    @abc.abstractmethod
    def collect(self, osdpl):
        pass

    @abc.abstractmethod
    def take_data(self):
        pass

    def refresh_data(self):
        if not self.can_collect_data:
            LOG.warning(
                f"Collector {self._name} is enabled, but collection for it is not possible."
            )
            self.data = {}
        self.data = self.take_data()

    @property
    @abc.abstractmethod
    def can_collect_data(self):
        pass
