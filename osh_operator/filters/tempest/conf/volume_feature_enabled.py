from osh_operator.filters.tempest import base_section


class VolumeFeatureEnabled(base_section.BaseSection):

    name = "volume-feature-enabled"
    options = [
        "api_extensions",
        "api_v1",
        "api_v2",
        "api_v3",
        "backup",
        "clone",
        "extend_attached_volume",
        "manage_snapshot",
        "manage_volume",
        "multi_backend",
        "snapshot",
    ]

    @property
    def api_extensions(self):
        pass

    @property
    def api_v1(self):
        pass

    @property
    def api_v2(self):
        pass

    @property
    def api_v3(self):
        pass

    @property
    def backup(self):
        pass

    @property
    def clone(self):
        pass

    @property
    def extend_attached_volume(self):
        pass

    @property
    def manage_snapshot(self):
        pass

    @property
    def manage_volume(self):
        pass

    @property
    def multi_backend(self):
        pass

    @property
    def snapshot(self):
        pass
