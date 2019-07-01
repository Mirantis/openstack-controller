from osh_operator.filters.tempest import base_section


DNS_FEATURES_RELEASE_MAPPING = {
    "queens": {
        "api_v1": False,
        "api_v2": True,
        "bug_1573141_fixed": True,
        "api_v2_quotas": True,
        "api_v2_root_recordsets": True,
    },
    "pike": {
        "api_v1": False,
        "api_v2": True,
        "bug_1573141_fixed": True,
        "api_v2_quotas": True,
        "api_v2_root_recordsets": True,
    },
    "ocata": {
        "api_v1": False,
        "api_v2": True,
        "bug_1573141_fixed": True,
        "api_v2_quotas": True,
        "api_v2_root_recordsets": True,
    },
    "newton": {
        "api_v1": False,
        "api_v2": True,
        "bug_1573141_fixed": True,
        "api_v2_quotas": True,
        "api_v2_root_recordsets": True,
    },
    "mitaka": {
        "api_v1": False,
        "api_v2": True,
        "bug_1573141_fixed": True,
        "api_v2_quotas": True,
        "api_v2_root_recordsets": True,
    },
}


class DnsFeatureEnabled(base_section.BaseSection):

    name = "dns_feature_enabled"
    options = [
        "api_admin",
        "api_v1",
        "api_v1_servers",
        "api_v2",
        "api_v2_quotas",
        "api_v2_quotas_verify_project",
        "api_v2_root_recordsets",
        "bug_1573141_fixed",
        "notification_nova_fixed",
        "notification_neutron_floatingip",
    ]

    @property
    def api_admin(self):
        pass

    @property
    def api_v1(self):
        pass

    @property
    def api_v1_servers(self):
        pass

    @property
    def api_v2(self):
        pass

    @property
    def api_v2_quotas(self):
        pass

    @property
    def api_v2_root_recordsets(self):
        pass

    @property
    def bug_1573141_fixed(self):
        pass

    @property
    def api_v2_quotas_verify_project(self):
        pass

    @property
    def notification_nova_fixed(self):
        return True

    @property
    def notification_neutron_floatingip(self):
        return True
