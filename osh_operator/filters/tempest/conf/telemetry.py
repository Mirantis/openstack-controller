from osh_operator.filters.tempest import base_section


class Telemetry(base_section.BaseSection):

    name = "telemetry"
    options = ["alarm_granularity"]

    @property
    def alarm_granularity(self):
        pass
