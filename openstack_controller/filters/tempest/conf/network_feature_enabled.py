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
            "quota_details",
            "provider",
            "standard-attr-tag",
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

        if (
            self.get_spec_item("features.neutron.dvr.enabled", False)
            and self.get_spec_item("features.neutron.backend", "ml2") == "ml2"
        ):
            api_extensions_default.append("dvr")

        if self.get_spec_item("features.neutron.backend") == "ml2":
            api_extensions_default.extend(
                [
                    "l3-ha",
                    "l3-flavors",
                    "l3_agent_scheduler",
                    "dhcp_agent_scheduler",
                ]
            )

        if self.get_spec_item("features.neutron.backend") in [
            "ml2",
            "ml2/ovn",
        ]:
            api_extensions_default.extend(
                [
                    "auto-allocated-topology",
                    "network-ip-availability",
                    "network_availability_zone",
                    "subnet_allocation",
                    "flavors",
                    "availability_zone",
                    "multi-provider",
                    "subnet-service-types",
                    "standard-attr-revisions",
                    "router_availability_zone",
                    "filter-validation",
                    "dns-domain-ports",
                    "dns-integration",
                    "default-subnetpools",
                    "ext-gw-mode",
                    "agent",
                    "net-mtu",
                    "address-scope",
                    "extraroute",
                    "rbac-policies",
                    "qos",
                    "qos-bw-limit-direction",
                    "qos-bw-minimum-ingress",
                    "qos-default",
                    "qos-fip",
                    "qos-gateway-ip",
                    "qos-port-network-policy",
                    "qos-pps-minimum",
                    "qos-pps-minimum-rule-alias",
                    "qos-pps",
                    "qos-rule-type-details",
                    "qos-rules-alias",
                    "subnetpool-prefix-ops",
                    "floatingip-pools",
                    "ip-substring-filtering",
                ]
            )
            if (
                constants.OpenStackVersion[self.spec["openstack_version"]]
                >= constants.OpenStackVersion["ussuri"]
            ):
                api_extensions_default.extend(
                    [
                        "rbac-address-scope",
                        "rbac-address-group",
                        "rbac-security-groups",
                        "rbac-subnetpool",
                        "stateful-security-group",
                        "fip-port-details",
                        "port-mac-address-regenerate",
                    ]
                )

            if (
                constants.OpenStackVersion[self.spec["openstack_version"]]
                >= constants.OpenStackVersion["victoria"]
            ):
                api_extensions_default.extend(["net-mtu-writable"])

            if (
                constants.OpenStackVersion[self.spec["openstack_version"]]
                >= constants.OpenStackVersion["wallaby"]
            ):
                api_extensions_default.extend(
                    ["address-group", "security-groups-remote-address-group"]
                )

            if (
                constants.OpenStackVersion[self.spec["openstack_version"]]
                >= constants.OpenStackVersion["xena"]
            ):
                api_extensions_default.extend(
                    ["port-resource-request", "port-resource-request-groups"]
                )

        if self.get_spec_item("features.neutron.bgpvpn.enabled"):
            api_extensions_default.extend(
                ["bgpvpn", "bgpvpn-routes-control", "bgpvpn-vni"]
            )
        if self.get_spec_item("features.neutron.vpnaas.enabled"):
            api_extensions_default.extend(["vpnaas"])

        if self.get_spec_item("features.neutron.backend") == "tungstenfabric":
            if (
                constants.OpenStackVersion[self.spec["openstack_version"]]
                >= constants.OpenStackVersion["victoria"]
            ):
                api_extensions_default.extend(["net-mtu", "net-mtu-writable"])

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
