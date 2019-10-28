from osh_operator.filters.tempest import base_section


class LoadBalancer(base_section.BaseSection):

    name = "load_balancer"
    options = [
        "region",
        "catalog_type",
        "endpoint_type",
        "build_interval",
        "build_timeout",
        "octavia_svc_username",
        "check_interval",
        "check_timeout",
        "lb_build_interval",
        "lb_build_timeout",
        "member_role",
        "admin_role",
        "scp_connection_timeout",
        "scp_connection_attempts",
        "provider",
        "RBAC_test_type",
        "enabled_provider_drivers",
        "loadbalancer_topology",
        "expected_flavor_capability",
        "disable_boot_network",
        "enable_security_groups",
        "vip_subnet_cidr",
        "vip_ipv6_subnet_cidr",
        "member_1_ipv4_subnet_cidr",
        "member_1_ipv6_subnet_cidr",
        "member_2_ipv4_subnet_cidr",
        "member_2_ipv6_subnet_cidr",
        "amphora_ssh_user",
        "amphora_ssh_key",
        "random_server_name_length",
        "availability_zone",
    ]

    @property
    def region(self):
        pass

    @property
    def catalog_type(self):
        pass

    @property
    def endpoint_type(self):
        pass

    @property
    def build_interval(self):
        pass

    @property
    def build_timeout(self):
        pass

    @property
    def octavia_svc_username(self):
        pass

    @property
    def check_interval(self):
        pass

    @property
    def check_timeout(self):
        pass

    @property
    def lb_build_interval(self):
        pass

    @property
    def lb_build_timeout(self):
        pass

    @property
    def member_role(self):
        pass

    @property
    def admin_role(self):
        pass

    @property
    def scp_connection_timeout(self):
        pass

    @property
    def scp_connection_attempts(self):
        pass

    @property
    def provider(self):
        pass

    @property
    def RBAC_test_type(self):
        pass

    @property
    def enabled_provider_drivers(self):
        pass

    @property
    def loadbalancer_topology(self):
        pass

    @property
    def expected_flavor_capability(self):
        pass

    @property
    def disable_boot_network(self):
        pass

    @property
    def enable_security_groups(self):
        # If 'security-group' in api_extension, return True
        return True

    @property
    def vip_subnet_cidr(self):
        pass

    @property
    def vip_ipv6_subnet_cidr(self):
        pass

    @property
    def member_1_ipv4_subnet_cidr(self):
        pass

    @property
    def member_1_ipv6_subnet_cidr(self):
        pass

    @property
    def member_2_ipv4_subnet_cidr(self):
        pass

    @property
    def member_2_ipv6_subnet_cidr(self):
        pass

    @property
    def amphora_ssh_user(self):
        pass

    @property
    def amphora_ssh_key(self):
        pass

    @property
    def random_server_name_length(self):
        pass

    @property
    def availability_zone(self):
        pass
