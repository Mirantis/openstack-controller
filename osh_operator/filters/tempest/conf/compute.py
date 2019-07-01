from osh_operator.filters.tempest import base_section


MICROVERSION_RELEASE_MAPPING = {
    "queens": {"min_microversion": "2.1", "max_microversion": "2.60"},
    "pike": {"min_microversion": "2.1", "max_microversion": "2.53"},
    "ocata": {"min_microversion": "2.1", "max_microversion": "2.42"},
    "newton": {"min_microversion": "2.1", "max_microversion": "2.42"},
    "mitaka": {"min_microversion": "2.1", "max_microversion": "2.42"},
}


class Compute(base_section.BaseSection):

    name = "compute"
    options = [
        "build_interval",
        "build_timeout",
        "catalog_type",
        "endpoint_type",
        "fixed_network_name",
        "flavor_ref",
        "flavor_ref_alt",
        "hypervisor_type",
        "image_ref",
        "image_ref_alt",
        "max_microversion",
        "min_compute_nodes",
        "min_microversion",
        "ready_wait",
        "region",
        "shelved_offload_time",
        "volume_device_name",
    ]

    @property
    def build_interval(self):
        pass

    @property
    def build_timeout(self):
        pass

    @property
    def catalog_type(self):
        pass

    @property
    def endpoint_type(self):
        pass

    @property
    def fixed_network_name(self):
        pass

    @property
    def flavor_ref(self):
        pass

    @property
    def flavor_ref_alt(self):
        pass

    @property
    def hypervisor_type(self):
        pass

    @property
    def image_ref(self):
        pass

    @property
    def image_ref_alt(self):
        pass

    @property
    def max_microversion(self):
        pass

    @property
    def min_compute_nodes(self):
        pass

    @property
    def min_microversion(self):
        pass

    @property
    def ready_wait(self):
        pass

    @property
    def region(self):
        pass

    @property
    def shelved_offload_time(self):
        pass

    @property
    def volume_device_name(self):
        pass
