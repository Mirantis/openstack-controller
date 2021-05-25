from openstack_controller.filters.tempest import base_section


class ImageSignatureVerification(base_section.BaseSection):
    name = "image_signature_verification"
    options = [
        "enforced",
    ]

    @property
    def enforced(self):
        return self.get_values_item(
            "nova", "conf.nova.glance.verify_glance_signatures", False
        )
