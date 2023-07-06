#!/usr/bin/env python3

import os

from openstack_controller.osctl.plugins.sosreport import base
from openstack_controller.osctl import utils as osctl_utils
from openstack_controller import utils
from openstack_controller import kube
from openstack_controller import settings

LOG = utils.get_logger(__name__)


class NovaObjectsCollector(base.BaseLogsCollector):
    name = "nova"

    @osctl_utils.generic_exception
    def collect_instances_info(self):
        for pod in kube.Pod.objects(kube.kube_client()).filter(
            namespace=settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
            selector={"application": "libvirt", "component": "libvirt"},
        ):
            instances = pod.exec(
                command=["virsh", "list", "--name"], container="libvirt"
            )["stdout"]
            host = pod.obj["spec"]["nodeName"]
            base_dir = os.path.join(self.workspace, host)
            libvirt_generic_info = [
                ("instances.txt", ["virsh", "list", "--name"]),
                ("nodecpumap.txt", ["virsh", "nodecpumap"]),
                ("nodecpustats.txt", ["virsh", "nodecpustats"]),
                ("nodeinfo.txt", ["virsh", "nodeinfo"]),
                ("nodememstats.txt", ["virsh", "nodememstats"]),
                ("sysinfo.txt", ["virsh", "sysinfo"]),
                ("version.txt", ["virsh", "version"]),
                ("capabilities.txt", ["virsh", "capabilities"]),
            ]
            for dst, command in libvirt_generic_info:
                self.dump_exec_result(
                    os.path.join(base_dir, dst),
                    pod.exec(command=command, container="libvirt"),
                )

            for instance in instances.strip().splitlines():
                domain_info = [
                    ("dumpxml.txt", ["virsh", "dumpxml", instance]),
                    ("domiflist.txt", ["virsh", "domiflist", instance]),
                    ("domblklist.txt", ["virsh", "domblklist", instance]),
                    ("error.txt", ["/bin/foo", "domblklist", instance]),
                ]
                for dst, command in domain_info:
                    self.dump_exec_result(
                        os.path.join(base_dir, instance, dst),
                        pod.exec(command=command, container="libvirt"),
                    )

    def get_tasks(self):
        res = []
        if "nova" in set(self.args.component):
            res.append((self.collect_instances_info, (), {}))
        return res
