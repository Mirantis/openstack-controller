#!/usr/bin/env python3
import abc
import os

from openstack_controller import kube


class BaseLogsCollector:
    name = ""
    registry = {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        cls.registry[cls.name] = cls

    def __init__(self, args):
        self.args = args
        self.workspace = os.path.join(args.workspace, self.name)
        self.hosts = self.get_hosts()

    def get_hosts(self):
        hosts = set()
        for host_pattern in set(self.args.host):
            if "=" in host_pattern:
                selector = {}
                for selector_pattern in host_pattern.split(","):
                    label, value = selector_pattern.split("=")
                    selector.update({label: value})
                for host in kube.Node.objects(kube.kube_client()).filter(
                    selector=selector,
                ):
                    hosts.add(host.name)
            else:
                hosts.add(host_pattern)
        return hosts

    def dump_exec_result(self, dst, res):
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        if res.get("stdout"):
            with open(dst, "w") as f:
                f.write(res["stdout"])
        if res.get("stderr"):
            with open(f"{dst}.error", "w") as f:
                f.write(res["stderr"])

    @abc.abstractmethod
    def get_tasks(self):
        """Returns tuple with task and arguments for logs collection."""
        pass
