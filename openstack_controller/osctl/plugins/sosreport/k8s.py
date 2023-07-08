#!/usr/bin/env python3

import os
import yaml

from openstack_controller.osctl.plugins.sosreport import base
from openstack_controller.osctl import utils as osctl_utils
from openstack_controller import utils
from openstack_controller import kube

LOG = utils.get_logger(__name__)


class K8sObjectsCollector(base.BaseLogsCollector):
    name = "k8s"

    def __init__(self, args, workspace):
        super().__init__(args, workspace)
        self.objects = {
            "openstack": {
                "PersistentVolumeClaim",
                "Deployment",
                "DaemonSet",
                "StatefulSet",
                "Pod",
                "Job",
            },
            "openstack-redis": {
                "PersistentVolumeClaim",
                "Deployment",
                "StatefulSet",
                "Pod",
                "Job",
            },
            "osh-system": {
                "Deployment",
                "Pod",
                "Job",
            },
            None: {"Node", "PersistentVolume"},
        }

    @osctl_utils.generic_exception
    def collect_objects(self):
        for namespace, kinds in self.objects.items():
            base_dir = os.path.join(self.workspace, "cluster")
            if namespace is not None:
                base_dir = os.path.join(
                    self.workspace, "namespaced", namespace
                )
            for kind in kinds:
                work_dir = os.path.join(base_dir, kind.lower())
                os.makedirs(work_dir, exist_ok=True)
                kube_class = kube.get_object_by_kind(kind)
                if kube_class is None:
                    LOG.warning(
                        "Kind: {kind} is not present in the cluster. Skip objects collection."
                    )
                for obj in (
                    kube_class.objects(kube.kube_client()).filter(
                        namespace=namespace
                    )
                    or []
                ):
                    dst = os.path.join(work_dir, obj.name)
                    with open(dst, "w") as f:
                        yaml.dump(obj.obj, f)

    def get_tasks(self):
        res = []
        res.append((self.collect_objects, (), {}))
        return res
