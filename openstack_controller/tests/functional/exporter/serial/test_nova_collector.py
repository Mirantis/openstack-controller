from openstack_controller.exporter.constants import ServiceState, ServiceStatus
from openstack_controller.tests.functional.exporter import base
from openstack_controller.tests.functional import waiters as wait


class NovaCollectorSerialFunctionalTestCase(
    base.BaseFunctionalExporterTestCase
):
    def setUp(self):
        super().setUp()
        svc = [
            svc
            for svc in self.ocm.compute_get_services()
            if svc["status"].lower() == "enabled"
        ][0]

        self.compute_svc_data = {"host": svc["host"], "binary": svc["binary"]}

    @property
    def compute_svc(self):
        return self.ocm.compute_get_services(**self.compute_svc_data)[0]

    def tearDown(self):
        self.ocm.compute_ensure_service_enabled(self.compute_svc)
        self.ocm.compute_ensure_service_force_down(self.compute_svc, False)
        super().tearDown()

    def test_service_status_enabled_disabled(self):
        metric_name = "osdpl_nova_service_status"
        self.ocm.compute_ensure_service_disabled(
            self.compute_svc,
            "Functional test test_service_status_enabled_disabled",
        )
        labels = {
            "host": self.compute_svc["host"],
            "binary": self.compute_svc["binary"],
        }
        wait.wait_for_compute_service_status(
            self.ocm, self.compute_svc, status="disabled"
        )
        self.wait_service_metric(
            metric_name, labels, value=ServiceStatus.disabled
        )
        self.ocm.compute_ensure_service_enabled(self.compute_svc)
        wait.wait_for_compute_service_status(self.ocm, self.compute_svc)
        self.wait_service_metric(
            metric_name, labels, value=ServiceStatus.enabled
        )

    def test_service_state_up_down(self):
        metric_name = "osdpl_nova_service_state"
        self.ocm.compute_ensure_service_force_down(self.compute_svc, True)
        labels = {
            "host": self.compute_svc["host"],
            "binary": self.compute_svc["binary"],
        }
        wait.wait_for_compute_service_state(
            self.ocm, self.compute_svc, state="down"
        )
        self.wait_service_metric(metric_name, labels, value=ServiceState.down)
        self.ocm.compute_ensure_service_force_down(self.compute_svc, False)
        wait.wait_for_compute_service_state(self.ocm, self.compute_svc)
        self.wait_service_metric(metric_name, labels, value=ServiceState.up)
