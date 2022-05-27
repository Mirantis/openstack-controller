from openstack_controller import constants
from openstack_controller.filters.tempest import base_section


class LoadBalancerFeatureEnabled(base_section.BaseSection):

    name = "loadbalancer-feature-enabled"
    options = [
        "not_implemented_is_error",
        "health_monitor_enabled",
        "terminated_tls_enabled",
        "l7_protocol_enabled",
        "pool_algorithms_enabled",
        "l4_protocol",
        "spare_pool_enabled",
        "session_persistence_enabled",
        "force_cleanup_enabled",
    ]

    @property
    def not_implemented_is_error(self):
        try:
            if self.spec["features"]["neutron"]["backend"] == "tungstenfabric":
                return False
        except:
            pass

    @property
    def health_monitor_enabled(self):
        try:
            if self.spec["features"]["neutron"]["backend"] == "tungstenfabric":
                return False
        except:
            pass

    @property
    def terminated_tls_enabled(self):
        try:
            if self.spec["features"]["neutron"]["backend"] == "tungstenfabric":
                return False
        except:
            pass

    @property
    def l7_protocol_enabled(self):
        pass

    @property
    def pool_algorithms_enabled(self):
        pass

    @property
    def l4_protocol(self):
        pass

    @property
    def spare_pool_enabled(self):
        pass

    @property
    def session_persistence_enabled(self):
        pass

    @property
    def force_cleanup_enabled(self):
        if (
            self.spec["openstack_version"] != "master"
            and constants.OpenStackVersion[self.spec["openstack_version"]]
            >= constants.OpenStackVersion["victoria"]
        ):
            return True
