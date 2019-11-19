from openstack_controller.filters.tempest import base_section


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
        return self.get_keystone_credential("password")

    @property
    def admin_project_name(self):
        return self.get_keystone_credential("project_name")

    @property
    def admin_username(self):
        return self.get_keystone_credential("username")

    @property
    def create_isolated_networks(self):
        pass

    @property
    def default_credentials_domain_name(self):
        pass

    @property
    def tempest_roles(self):
        roles = []
        if self.is_service_enabled("barbican"):
            roles.append("creator")
        if roles:
            return ", ".join(roles)

    @property
    def test_accounts_file(self):
        pass

    @property
    def use_dynamic_credentials(self):
        # This option requires that OpenStack Identity API
        # admin credentials are known.
        admin_username = self.get_keystone_credential("username")
        admin_password = self.get_keystone_credential("password")

        if admin_username and admin_password:
            return True
        return False
