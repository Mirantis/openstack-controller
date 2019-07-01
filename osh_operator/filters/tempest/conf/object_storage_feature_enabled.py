from osh_operator.filters.tempest import base_section


class ObjectStorageFeatureEnabled(base_section.BaseSection):

    name = "object-storage-feature-enabled"
    options = [
        "container_sync",
        "discoverability",
        "discoverable_apis",
        "object_versioning",
    ]

    @property
    def container_sync(self):
        pass

    @property
    def discoverability(self):
        pass

    @property
    def discoverable_apis(self):
        pass

    @property
    def object_versioning(self):
        pass
