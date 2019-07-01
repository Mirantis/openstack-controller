from osh_operator.filters.tempest import base_section


class BaremetalFeatureEnabled(base_section.BaseSection):

    name = "baremetal_feature_enabled"
    options = ["ipxe_enabled"]

    @property
    def ipxe_enabled(self):
        pass
