import logging

import pykube
import datetime

from openstack_controller import version
from openstack_controller import layers
from openstack_controller import kube

LOG = logging.getLogger(__name__)


# When start applying changes
APPLYING = "APPLYING"
# When changes are applied
APPLIED = "APPLIED"
# When start deleting service
DELETING = "DELETING"
# When waiting for Applying changes, ie waiting other services to upgrade
WAITING = "WAITING"


class OpenStackDeploymentStatus(pykube.objects.NamespacedAPIObject):
    version = "lcm.mirantis.com/v1alpha1"
    kind = "OpenStackDeploymentStatus"
    endpoint = "openstackdeploymentstatus"
    kopf_on_args = *version.split("/"), endpoint

    def __init__(self, name, namespace, *args, **kwargs):
        self.dummy = {
            "apiVersion": self.version,
            "kind": self.kind,
            "metadata": {"name": name, "namespace": namespace},
            "spec": {},
            "status": {},
        }
        return super().__init__(kube.api, self.dummy)

    def present(self):
        if not self.exists():
            self.create()

    def absent(self):
        if self.exists():
            self.delete()

    def set_osdpl_state(self, state):
        self.patch({"status": {"osdpl": {"state": state}}})

    def _generate_osdpl_status_generic(self, osdpl_spec):
        timestamp = datetime.datetime.utcnow()
        osdpl_generic = {
            "openstack_version": osdpl_spec["openstack_version"],
            "controller_version": version.release_string,
            "fingerprint": layers.spec_hash(osdpl_spec),
            "timestamp": str(timestamp),
        }
        return osdpl_generic

    def set_osdpl_status(self, state, osdpl_spec, osdpl_diff, osdpl_cause):
        patch = self._generate_osdpl_status_generic(osdpl_spec)
        patch["changes"] = str(osdpl_diff)
        patch["cause"] = osdpl_cause
        patch["state"] = state
        self.patch({"status": {"osdpl": patch}})

    def set_service_status(self, service_name, state, osdpl_spec):
        patch = self._generate_osdpl_status_generic(osdpl_spec)
        patch["state"] = state
        self.patch({"status": {"services": {service_name: patch}}})

    def set_service_state(self, service_name, state):
        self.patch({"status": {"services": {service_name: {"state": state}}}})

    def remove_service_status(self, service_name):
        self.patch({"status": {"services": {service_name: None}}})

    def set_osdpl_health(self, health):
        self.patch({"status": {"health": health}})
