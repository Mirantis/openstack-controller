import logging

import pykube
import datetime

from openstack_controller import version
from openstack_controller import layers
from openstack_controller import kube

LOG = logging.getLogger(__name__)


APPLYING = "APPLYING"
APPLIED = "APPLIED"
DELETING = "DELETING"


class OpenStackDeploymentStatus(pykube.objects.NamespacedAPIObject):
    version = "lcm.mirantis.com/v1alpha1"
    kind = "OpenStackDeploymentStatus"
    endpoint = "openstackdeploymentstatus"
    kopf_on_args = *version.split("/"), endpoint

    def __init__(self, name, namespace, osdpl, *args, **kwargs):
        self.dummy = {
            "apiVersion": self.version,
            "kind": self.kind,
            "metadata": {"name": name, "namespace": namespace},
            "spec": {},
            "status": {},
        }
        self.osdpl = osdpl
        return super().__init__(kube.api, self.dummy)

    def present(self):
        if not self.exists():
            self.create()

    def absent(self):
        if self.exists():
            self.delete()

    def set_osdpl_state(self, state):
        self.patch({"status": {"osdpl": {"state": state}}})

    def _generate_osdpl_status_generic(self):
        timestamp = datetime.datetime.utcnow()
        osdpl_generic = {
            "openstack_version": self.osdpl["body"]["spec"][
                "openstack_version"
            ],
            "controller_version": version.release_string,
            "cause": self.osdpl["kwargs"]["cause"].event,
            "changes": str(self.osdpl["kwargs"]["diff"]),
            "fingerprint": layers.spec_hash(self.osdpl["body"]["spec"]),
            "timestamp": str(timestamp),
        }
        return osdpl_generic

    def set_osdpl_status(self, state):
        patch = self._generate_osdpl_status_generic()
        patch["state"] = state
        self.patch({"status": {"osdpl": patch}})

    def set_service_status(self, service_name, state):
        patch = self._generate_osdpl_status_generic()
        patch["state"] = state
        self.patch({"status": {"services": {service_name: patch}}})

    def remove_service_status(self, service_name):
        self.patch({"status": {"services": {service_name: None}}})
