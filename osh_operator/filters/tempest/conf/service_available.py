from osh_operator.filters.tempest import base_section


class ServiceAvailable(base_section.BaseSection):

    name = "service_available"
    options = [
        "aodh",
        "barbican",
        "cinder",
        "ceilometer",
        "contrail",
        "designate",
        "glance",
        "gnocchi",
        "heat",
        "ironic",
        "manila",
        "neutron",
        "nova",
        "panko",
        "sahara",
        "swift",
        "horizon",
        "keystone",
        "load_balancer",
    ]

    def _is_service_enabled(self, service):
        """Check if service is enabled in specific environment.

        We assume service is enabled when API for this serivce is
        enabled at least on one node in the cloud.

        :param service:
        :param pillars:
        """
        for component_name, component in self.helmbundles_body.items():
            for release in component.get("spec", {}).get("releases", []):
                chart_name = release["chart"].split("/")[-1]
                if chart_name == service:
                    return True
        return False

    @property
    def aodh(self):
        return self._is_service_enabled("aodh")

    @property
    def barbican(self):
        return self._is_service_enabled("barbican")

    @property
    def cinder(self):
        return self._is_service_enabled("cinder")

    @property
    def ceilometer(self):
        return self._is_service_enabled("ceilometer")

    @property
    def contrail(self):
        return self._is_service_enabled("opencontrail")

    @property
    def designate(self):
        return self._is_service_enabled("designate")

    @property
    def glance(self):
        return self._is_service_enabled("glance")

    @property
    def gnocchi(self):
        return self._is_service_enabled("gnocchi")

    @property
    def heat(self):
        return self._is_service_enabled("heat")

    @property
    def ironic(self):
        return self._is_service_enabled("ironic")

    @property
    def manila(self):
        return self._is_service_enabled("manila")

    @property
    def neutron(self):
        return self._is_service_enabled("neutron")

    @property
    def nova(self):
        return self._is_service_enabled("nova")

    @property
    def panko(self):
        return self._is_service_enabled("panko")

    @property
    def sahara(self):
        return self._is_service_enabled("sahara")

    @property
    def swift(self):
        pass

    @property
    def horizon(self):
        return self._is_service_enabled("horizon")

    @property
    def keystone(self):
        return self._is_service_enabled("keystone")

    @property
    def load_balancer(self):
        return self._is_service_enabled("octavia")
