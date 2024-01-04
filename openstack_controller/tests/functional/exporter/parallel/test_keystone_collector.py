from openstack_controller.tests.functional.exporter import base


class KeystoneCollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    known_metrics = {
        "osdpl_keystone_projects": {"labels": []},
        "osdpl_keystone_users": {"labels": []},
        "osdpl_keystone_domains": {"labels": []},
    }

    def test_keystone_projects_value(self):
        projects_total = 0
        for domain in self.ocm.oc.identity.domains():
            projects_total += len(
                list(self.ocm.oc.identity.projects(domain_id=domain["id"]))
            )
        metric = self.get_metric("osdpl_keystone_projects")
        self.assertEqual(
            projects_total,
            metric.samples[0].value,
        )

    def test_keystone_users_value(self):
        users_total = 0
        for domain in self.ocm.oc.identity.domains():
            users_total += len(
                list(self.ocm.oc.identity.users(domain_id=domain["id"]))
            )
        metric = self.get_metric("osdpl_keystone_users")
        self.assertEqual(
            users_total,
            metric.samples[0].value,
        )

    def test_keystone_domains(self):
        domains_total = len(list(self.ocm.oc.identity.domains()))
        metric = self.get_metric("osdpl_keystone_domains")
        self.assertEqual(
            domains_total,
            metric.samples[0].value,
        )
