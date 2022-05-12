from openstack_controller.filters.tempest import base_section


MULTIATTACH_CEPH_RELEASE_MAPPING = {
    "yoga": True,
    "xena": True,
    "wallaby": True,
    "victoria": True,
    "ussuri": False,
    "train": False,
    "stein": False,
    "rocky": False,
    "queens": False,
    "pike": False,
    "ocata": False,
    "newton": False,
    "mitaka": False,
    "kilo": False,
}


class ComputeFeatureEnabled(base_section.BaseSection):

    name = "compute-feature-enabled"
    options = [
        "api_extensions",
        "attach_encrypted_volume",
        "barbican_integration_enabled",
        "boot_from_volume",
        "block_migrate_cinder_iscsi",
        "block_migration_for_live_migration",
        "change_password",
        "cold_migration",
        "config_drive",
        "console_output",
        "disk_config",
        "enable_instance_password",
        "interface_attach",
        "live_migrate_back_and_forth",
        "live_migration",
        "metadata_service",
        "nova_cert",
        "pause",
        "personality",
        "rdp_console",
        "rescue",
        "resize",
        "scheduler_available_filters",
        "serial_console",
        "shelve",
        "snapshot",
        "spice_console",
        "suspend",
        "swap_volume",
        "vnc_console",
        "vnc_server_header",
        "volume_multiattach",
    ]

    @property
    def api_extensions(self):
        pass

    @property
    def attach_encrypted_volume(self):
        if (
            self.get_values_item("cinder", "conf.cinder.keymgr.api_class")
            == "cinder.keymgr.barbican.BarbicanKeyManager"
            and self.get_values_item("nova", "conf.nova.keymgr.api_class")
            == "nova.keymgr.barbican.BarbicanKeyManager"
        ):
            return True
        else:
            return False

    @property
    def barbican_integration_enabled(self):
        return self.get_values_item(
            "nova", "conf.nova.glance.verify_glance_signatures", False
        )

    @property
    def boot_from_volume(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def block_migrate_cinder_iscsi(self):
        pass

    @property
    def block_migration_for_live_migration(self):
        if self.get_values_item("nova", "conf.nova.libvirt.images_type") in [
            "qcow2",
        ]:
            return True
        else:
            return False

    @property
    def change_password(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def cold_migration(self):
        if self.get_values_item("nova", "conf.nova.libvirt.images_type") in [
            "lvm",
        ]:
            return False
        if self.is_service_enabled("ironic"):
            return False
        return True

    @property
    def config_drive(self):
        pass

    @property
    def console_output(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def disk_config(self):
        pass

    @property
    def enable_instance_password(self):
        pass

    @property
    def interface_attach(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def live_migrate_back_and_forth(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def live_migration(self):
        if self.get_values_item("nova", "conf.nova.libvirt.images_type") in [
            "lvm",
        ]:
            return False
        if self.is_service_enabled("ironic"):
            return False

    @property
    def metadata_service(self):
        pass

    @property
    def nova_cert(self):
        pass

    @property
    def pause(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def personality(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def rdp_console(self):
        pass

    @property
    def rescue(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def resize(self):
        if self.get_values_item("nova", "conf.nova.libvirt.images_type") in [
            "lvm",
        ]:
            return False
        if self.is_service_enabled("ironic"):
            return False
        return True

    @property
    def scheduler_available_filters(self):
        if self.get_spec_item("openstack_version").lower() in [
            "queens",
            "rocky",
        ]:
            return ",".join(
                [
                    "RetryFilter",
                    "AvailabilityZoneFilter",
                    "ComputeFilter",
                    "ComputeCapabilitiesFilter",
                    "ImagePropertiesFilter",
                    "ServerGroupAntiAffinityFilter",
                    "ServerGroupAffinityFilter",
                ]
            )

    @property
    def serial_console(self):
        pass

    @property
    def shelve(self):
        if self.is_service_enabled("ironic"):
            return False
        if self.get_values_item(
            "nova", "conf.nova.glance.verify_glance_signatures", False
        ):
            return False

    @property
    def snapshot(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def spice_console(self):
        pass

    @property
    def suspend(self):
        if self.is_service_enabled("ironic"):
            return False

    @property
    def swap_volume(self):
        pass

    @property
    def vnc_console(self):
        pass

    @property
    def vnc_server_header(self):
        pass

    @property
    def volume_multiattach(self):
        """
            This option depends on the used Cinder backend driver:

        - Ceph driver supports volume_multiattach from Stein
        - LVM driver supports volume_multiattach from Queens

        but we've decided not to test it on the Openstack versions older than
        Victoria.
        """
        version = self.spec["openstack_version"]
        return MULTIATTACH_CEPH_RELEASE_MAPPING.get(version)
