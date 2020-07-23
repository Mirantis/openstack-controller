from openstack_controller import constants
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
        api_extensions_default = [
            "binding",
            "external-net",
            "quotas",
            "provider",
            "standard-attr-timestamp",
            "service-type",
            "port-security",
            "extra_dhcp_opt",
            "pagination",
            "sorting",
            "security-group",
            "standard-attr-description",
            "router",
            "allowed-address-pairs",
            "project-id",
        ]

        if self.get_spec_item("features.neutron.dvr.enabled", False):
            api_extensions_default.append("dvr")

        if self.get_spec_item("features.neutron.backend") == "ml2":
            api_extensions_default.extend(
                [
                    "auto-allocated-topology",
                    "network-ip-availability",
                    "network_availability_zone",
                    "subnet_allocation",
                    "flavors",
                    "availability_zone",
                    "l3-ha",
                    "multi-provider",
                    "subnet-service-types",
                    "l3-flavors",
                    "standard-attr-revisions",
                    "router_availability_zone",
                    "filter-validation",
                    "dns-domain-ports",
                    "dns-integration",
                    "qos",
                    "qos-default",
                    "qos-rule-type-details",
                    "qos-bw-limit-direction",
                    "qos-fip",
                    "default-subnetpools",
                    "ext-gw-mode",
                    "agent",
                    "l3_agent_scheduler",
                    "net-mtu",
                    "address-scope",
                    "extraroute",
                    "dhcp_agent_scheduler",
                    "rbac-policies",
                    "standard-attr-tag",
                ]
            )
            if (
                constants.OpenStackVersion[self.spec["openstack_version"]]
                >= constants.OpenStackVersion["ussuri"]
            ):
                api_extensions_default.append("rbac-address-scope")

        return ", ".join(api_extensions_default)

    @property
    def floating_ips(self):
        pass

    @property
    def ipv6(self):
        return True

    @property
    def ipv6_subnet_attributes(self):
        return True

    @property
    def port_admin_state_change(self):
        pass

    @property
    def port_security(self):
        # TODO:(PRODX-1206)Need to generate 'api_extensions' in openstack-networking helmbundle.
        # In this case we should check that 'port_security' locate in 'api_extensions'.
        if self.is_service_enabled("neutron"):
            return True
