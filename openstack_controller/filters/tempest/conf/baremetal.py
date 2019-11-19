from openstack_controller.filters.tempest import base_section


IRONIC_MICROVERSION_RELEASE_MAPPING = {
    "train": {"min_microversion": "1.1", "max_microversion": "1.58"},
    "stein": {"min_microversion": "1.1", "max_microversion": "1.56"},
    "rocky": {"min_microversion": "1.1", "max_microversion": "1.46"},
    "queens": {"min_microversion": "1.1", "max_microversion": "1.38"},
    "pike": {"min_microversion": "1.1", "max_microversion": "1.34"},
    "ocata": {"min_microversion": "1.1", "max_microversion": "1.31"},
    "newton": {"min_microversion": "1.1", "max_microversion": "1.22"},
    "mitaka": {"min_microversion": "1.1", "max_microversion": "1.16"},
}


class Baremetal(base_section.BaseSection):

    name = "baremetal"
    options = [
        "active_timeout",
        "adjusted_root_disk_size_gb",
        "association_timeout",
        "catalog_type",
        "deploywait_timeout",
        "driver",
        "enabled_deploy_interfaces",
        "enabled_drivers",
        "enabled_hardware_types",
        "endpoint_type",
        "max_microversion",
        "min_microversion",
        "partition_image_ref",
        "power_timeout",
        "unprovision_timeout",
        "use_provision_network",
        "whole_disk_image_checksum",
        "whole_disk_image_ref",
        "whole_disk_image_url",
    ]

    @property
    def active_timeout(self):
        pass

    @property
    def adjusted_root_disk_size_gb(self):
        pass

    @property
    def association_timeout(self):
        pass

    @property
    def catalog_type(self):
        pass

    @property
    def deploywait_timeout(self):
        pass

    @property
    def driver(self):
        pass

    @property
    def enabled_deploy_interfaces(self):
        pass

    @property
    def enabled_drivers(self):
        pass

    @property
    def enabled_hardware_types(self):
        pass

    @property
    def endpoint_type(self):
        pass

    @property
    def max_microversion(self):
        ironic_enabled = self.is_service_enabled("ironic")
        version = self.spec["openstack_version"]
        if (
            ironic_enabled
            and version
            and version in IRONIC_MICROVERSION_RELEASE_MAPPING
        ):
            return IRONIC_MICROVERSION_RELEASE_MAPPING[version][
                "max_microversion"
            ]

    @property
    def min_microversion(self):
        ironic_enabled = self.is_service_enabled("ironic")
        version = self.spec["openstack_version"]
        if (
            ironic_enabled
            and version
            and version in IRONIC_MICROVERSION_RELEASE_MAPPING
        ):
            return IRONIC_MICROVERSION_RELEASE_MAPPING[version][
                "min_microversion"
            ]

    @property
    def partition_image_ref(self):
        pass

    @property
    def power_timeout(self):
        pass

    @property
    def unprovision_timeout(self):
        pass

    @property
    def use_provision_network(self):
        pass

    @property
    def whole_disk_image_checksum(self):
        pass

    @property
    def whole_disk_image_ref(self):
        pass

    @property
    def whole_disk_image_url(self):
        pass
