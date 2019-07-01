from osh_operator.filters.tempest import base_section


class Dashboard(base_section.BaseSection):

    name = "dashboard"
    options = [
        "dashboard_url",
        "login_url",
        "disable_ssl_certificate_validation",
    ]

    @property
    def dashboard_url(self):
        pass

    @property
    def login_url(self):
        pass

    @property
    def disable_ssl_certificate_validation(self):
        pass
