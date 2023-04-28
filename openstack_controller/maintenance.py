import datetime
import logging

import enum
import pykube

from openstack_controller import constants as const
from openstack_controller import kube
from openstack_controller import settings

LOG = logging.getLogger(__name__)
CONF = settings.CONF

MAINTENANCE_DEFAULT_NODE_CONFIG = {
    # The migration mode for instances present on the host either
    # live, manual or skip.
    # *live - oc will try to automatically live migrate instances
    # TODO(vsaienko): NOT IMPLEMENTED *live+cold - oc will try to automatically live migrate instances, in case of failure fallback to cold migration
    # TODO(vsaienko): NOT IMPLEMENTED 0*cold - oc will do cold migration for instances
    # *manual - oc do not touch instances, wait while they will be migrated manually.
    # *skip - do not call migration for instances, release lock and allow host reboot.
    "instance_migration_mode": {"default": "live", "type": "string"},
    # The number of attempts we trying to migrate instance before give up.
    "instance_migration_attempts": {"default": "3", "type": "int"},
}


# Maximum number of nodes upgraded in parallel.
def get_max_parallel_by_role(role):
    return {
        const.NodeRole.controller.value: 1,
        const.NodeRole.gateway.value: CONF.getint(
            "maintenance", "nwl_parallel_max_gateway"
        ),
        const.NodeRole.compute.value: CONF.getint(
            "maintenance", "nwl_parallel_max_compute"
        ),
    }[role]


class NodeMaintenanceConfig:
    opts_prefix = "openstack.lcm.mirantis.com"

    def __init__(self, node):
        self.node = node
        self._initialize_maintenance_opts()

    def _cast_to_type(self, value, type):
        if type == "string":
            return str(value)
        if type == "int":
            return int(value)
        if type == "bool":
            value = value.lower()
            if value in const.TRUE_STRINGS:
                return True
            elif value in const.FALSE_STRINGS:
                return False
        raise TypeError(
            f"Failed to process option value: {value} with type: {type}"
        )

    def _initialize_maintenance_opts(self):
        self.node.reload()
        for opt_name, opt in MAINTENANCE_DEFAULT_NODE_CONFIG.items():
            annotation_name = f"{self.opts_prefix}/{opt_name}"
            opt_val = self.node.metadata["annotations"].get(
                annotation_name, opt["default"]
            )
            value = self._cast_to_type(opt_val, type=opt["type"])
            setattr(self, opt_name, value)


class LockState(enum.Enum):
    active = "active"
    inactive = "inactive"
    failed = "failed"


class LockInnerState(enum.Enum):
    active = "active"  # We are progressing with the node
    inactive = "inactive"  # We finished with the node


class MaintenanceRequestScope(enum.Enum):
    drain = "drain"  # drain pods, no os reboot
    os = "os"  # include drain + potential os reboot


class LockBase(pykube.objects.APIObject):
    version = "lcm.mirantis.com/v1alpha1"
    workload = "openstack"

    @classmethod
    def _base_spec(cls, name):
        return {"controllerName": cls.workload}

    @classmethod
    def get_resource(cls, name):
        spec = {}
        spec.update(cls._base_spec(name))
        dummy = {
            "apiVersion": cls.version,
            "kind": cls.kind,
            "metadata": {"name": f"{cls.workload}-{name}"},
            "spec": spec,
        }
        return cls(kube.api, dummy)

    def present(self):
        if not self.exists():
            self.create()
            # Explicitly set state to active to do not rely on default.
            self.set_state(LockState.active.value)
        if settings.OSCTL_CLUSTER_RELEASE:
            # NOTE(vsaienko): reset cwl to active if it was set to inactive
            # by previous controller. PRODX-22757
            if self.get_release() != settings.OSCTL_CLUSTER_RELEASE:
                self.set_state(LockState.active.value)
                self.set_release(settings.OSCTL_CLUSTER_RELEASE)

    def absent(self):
        if self.exists():
            self.delete()

    def is_active(self):
        self.reload()
        return self.obj["status"]["state"] == LockState.active.value

    def is_maintenance(self):
        self.reload()
        return self.get_inner_state() == LockInnerState.active.value

    def set_state(self, state):
        self.patch({"status": {"state": state}}, subresource="status")

    def set_state_active(self):
        self.set_state(LockState.active.value)

    def set_release(self, release):
        self.patch({"status": {"release": release}}, subresource="status")

    def get_release(self):
        self.reload()
        return self.obj["status"].get("release", None)

    def set_state_inactive(self):
        self.set_state(LockState.inactive.value)

    def set_inner_state(self, state):
        self.patch({"metadata": {"annotations": {"inner_state": state}}})

    def set_inner_state_active(self):
        self.set_inner_state(LockInnerState.active.value)

    def set_inner_state_inactive(self):
        self.set_inner_state(LockInnerState.inactive.value)

    def get_inner_state(self):
        return self.obj["metadata"].get("annotations", {}).get("inner_state")

    def set_error_message(self, msg):
        timestamp = datetime.datetime.utcnow()
        msg = f"{timestamp} {msg}"
        self.patch({"status": {"errorMessage": msg}}, subresource="status")

    def unset_error_message(self):
        self.patch({"status": {"errorMessage": None}}, subresource="status")


class ClusterWorkloadLock(LockBase):
    endpoint = "clusterworkloadlocks"
    kind = "ClusterWorkloadLock"


class NodeWorkloadLock(LockBase):
    endpoint = "nodeworkloadlocks"
    kind = "NodeWorkloadLock"

    @classmethod
    def _base_spec(cls, name):
        spec = super()._base_spec(name)
        spec["nodeName"] = name
        return spec

    @staticmethod
    def required_for_node(node: pykube.Node) -> bool:
        # We create workloadlock for all nodes we know about.
        for role in const.NodeRole:
            if node.has_role(role):
                return True
        return False

    @classmethod
    def get_all(cls):
        return [
            o
            for o in cls.objects(kube.api)
            if o.obj["spec"]["controllerName"] == cls.workload
        ]

    def maintenance_locks(self):
        locks = {role.value: [] for role in const.NodeRole}
        for nwl in self.get_all():
            if nwl.is_maintenance():
                node = kube.find(kube.Node, nwl.obj["spec"]["nodeName"])
                for role in const.NodeRole:
                    if node.has_role(role):
                        locks[role.value].append(nwl)
        return locks

    def can_handle_nmr(self):
        """Check if we can handle more NodeMaintenanceRequests

        Compare current number of active NodeMaintenanceRequests with
        maximum allowed number of parallel nodes.

        return: False if can't handle additional request. True othervise.
        """
        active_locks = self.maintenance_locks()
        for role, locks in active_locks.items():
            len_locks = len(locks)
            if len_locks >= get_max_parallel_by_role(role):
                node_name = self.obj["spec"]["nodeName"]
                LOG.info(
                    f"Handling Nodemaintenancerequest for node {node_name} is not allowed. Already handling {locks} for role: {role}"
                )
                return False
        return True


class MaintenanceRequestBase(pykube.objects.APIObject):
    version = "lcm.mirantis.com/v1alpha1"

    @classmethod
    def get_resource(cls, data):
        return cls(kube.api, data)

    def get_scope(self):
        return self.obj["spec"]["scope"]

    def is_reboot_possible(self):
        return self.get_scope() == MaintenanceRequestScope.os.value


class NodeMaintenanceRequest(MaintenanceRequestBase):
    version = "lcm.mirantis.com/v1alpha1"
    endpoint = "nodemaintenancerequests"
    kind = "NodeMaintenanceRequest"
    kopf_on_args = *version.split("/"), endpoint


class ClusterMaintenanceRequest(MaintenanceRequestBase):
    version = "lcm.mirantis.com/v1alpha1"
    endpoint = "clustermaintenancerequests"
    kind = "ClusterMaintenanceRequest"
    kopf_on_args = *version.split("/"), endpoint
