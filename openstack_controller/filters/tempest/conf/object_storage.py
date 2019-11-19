from openstack_controller.filters.tempest import base_section


class ObjectStorage(base_section.BaseSection):

    name = "object-storage"
    options = [
        "api_prefix",
        "catalog_type",
        "cluster_name",
        "container_sync_interval",
        "container_sync_timeout",
        "endpoint_type",
        "operator_role",
        "realm_name",
        "region",
        "reseller_admin_role",
    ]

    @property
    def api_prefix(self):
        pass

    @property
    def catalog_type(self):
        pass

    @property
    def cluster_name(self):
        pass

    @property
    def container_sync_interval(self):
        pass

    @property
    def container_sync_timeout(self):
        pass

    @property
    def endpoint_type(self):
        pass

    @property
    def operator_role(self):
        pass

    @property
    def realm_name(self):
        pass

    @property
    def region(self):
        pass

    @property
    def reseller_admin_role(self):
        pass
