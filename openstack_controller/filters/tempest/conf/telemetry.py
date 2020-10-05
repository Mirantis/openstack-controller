from openstack_controller.filters.tempest import base_section


class Telemetry(base_section.BaseSection):

    name = "telemetry"
    options = ["alarm_granularity"]

    @property
    def alarm_granularity(self):
        ceilometer_enabled = self.is_service_enabled("ceilometer")
        if ceilometer_enabled:
            archive_policy_values = {
                "ceilometer-low": 60,
                "ceilometer-low-rate": 60,
                "ceilometer-high-static": 3600,
                "ceilometer-high-static-rate": 3600,
            }

            resources = self.get_values_item(
                "ceilometer", "conf.gnocchi_resources.resources", []
            )
            for res in resources:
                # check all resources and find the first with type instance and
                # return granularity related to policy name in archive_policy_values
                if res.get("resource_type") == "instance" and isinstance(
                    res.get("metrics"), dict
                ):
                    policy_name = (
                        res["metrics"]
                        .get("cpu", {})
                        .get("archive_policy_name")
                    )
                    if (
                        policy_name
                        and policy_name in archive_policy_values.keys()
                    ):
                        return archive_policy_values[policy_name]
