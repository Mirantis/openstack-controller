from openstack_controller.filters.tempest import base_section


class IdentityFeatureEnabled(base_section.BaseSection):
    name = "identity-feature-enabled"
    options = [
        "api_extensions",
        "api_v2",
        "api_v2_admin",
        "api_v3",
        "application_credentials",
        "domain_specific_drivers",
        "forbid_global_implied_dsr",
        "security_compliance",
        "trust",
    ]

    @property
    def api_extensions(self):
        pass

    @property
    def api_v2(self):
        pass

    @property
    def api_v2_admin(self):
        pass

    @property
    def api_v3(self):
        pass

    @property
    def application_credentials(self):
        # ['external', 'password', 'token', 'oauth1', 'mapped', 'application_credential']
        # These default values from upstream
        # https://opendev.org/openstack/keystone/src/branch/stable/stein/keystone/conf/constants.py
        return "application_credential" in self.get_values_item(
            "keystone",
            "conf.keystone.auth.methods",
            (
                "external",
                "password",
                "token",
                "oauth1",
                "mapped",
                "application_credential",
            ),
        )

    @property
    def domain_specific_drivers(self):
        pass

    @property
    def forbid_global_implied_dsr(self):
        pass

    @property
    def security_compliance(self):
        pass

    @property
    def trust(self):
        pass
