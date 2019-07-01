from osh_operator.filters.tempest import base_section


class Volume(base_section.BaseSection):

    name = "volume"
    options = [
        "backend_names",
        "build_interval",
        "build_timeout",
        "catalog_type",
        "disk_format",
        "endpoint_type",
        "manage_snapshot_ref",
        "manage_volume_ref",
        "max_microversion",
        "min_microversion",
        "region",
        "storage_protocol",
        "vendor_name",
        "volume_size",
    ]

    @property
    def backend_names(self):
        pass

    @property
    def build_interval(self):
        pass

    @property
    def build_timeout(self):
        pass

    @property
    def catalog_type(self):
        return "volumev2"

    @property
    def disk_format(self):
        pass

    @property
    def endpoint_type(self):
        pass

    @property
    def manage_snapshot_ref(self):
        pass

    @property
    def manage_volume_ref(self):
        pass

    @property
    def max_microversion(self):
        pass

    @property
    def min_microversion(self):
        pass

    @property
    def region(self):
        pass

    @property
    def storage_protocol(self):
        pass

    @property
    def vendor_name(self):
        pass

    @property
    def volume_size(self):
        pass
