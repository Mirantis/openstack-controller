from openstack_controller.filters.tempest import base_section


class NetworkFeatureEnabled(base_section.BaseSection):

    name = "network-feature-enabled"
    options = [
        "api_extensions",
        "floating_ips",
        "ipv6",
        "ipv6_subnet_attributes",
        "port_admin_state_change",
        "port_security",
    ]

    @property
    def api_extensions(self):
        pass

    @property
    def floating_ips(self):
        pass

    @property
    def ipv6(self):
        pass

    @property
    def ipv6_subnet_attributes(self):
        pass

    @property
    def port_admin_state_change(self):
        pass

    @property
    def port_security(self):
        # TODO:(PRODX-1206)Need to generate 'api_extensions' in openstack-networking helmbundle.
        # In this case we should check that 'port_security' locate in 'api_extensions'.
        if self.is_service_enabled("neutron"):
            return True
