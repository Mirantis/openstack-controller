from openstack_controller.filters.tempest import base_section


class Image(base_section.BaseSection):

    name = "image"
    options = [
        "build_interval",
        "build_timeout",
        "catalog_type",
        "container_formats",
        "disk_formats",
        "endpoint_type",
        "http_image",
        "region",
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
    def container_formats(self):
        pass

    @property
    def disk_formats(self):
        pass

    @property
    def endpoint_type(self):
        pass

    @property
    def http_image(self):
        images = self.get_values_item("glance", "bootstrap.structured.images")
        if images:
            image = list(images.values())[0]
            return image["source_url"] + image["image_file"]

    @property
    def region(self):
        return self.get_values_item(
            "keystone", "endpoints.identity.auth.admin.region"
        )
