from osh_operator.filters.tempest import base_section


class Auth(base_section.BaseSection):

    name = "auth"
    options = [
        "admin_domain_name",
        "admin_password",
        "admin_project_name",
        "admin_username",
        "create_isolated_networks",
        "default_credentials_domain_name",
        "tempest_roles",
        "test_accounts_file",
        "use_dynamic_credentials",
    ]

    @property
    def admin_domain_name(self):
        return "Default"

    @property
    def admin_password(self):
        pass

    @property
    def admin_project_name(self):
        pass

    @property
    def admin_username(self):
        pass

    @property
    def create_isolated_networks(self):
        pass

    @property
    def default_credentials_domain_name(self):
        pass

    @property
    def tempest_roles(self):
        pass

    @property
    def test_accounts_file(self):
        pass

    @property
    def use_dynamic_credentials(self):
        pass
