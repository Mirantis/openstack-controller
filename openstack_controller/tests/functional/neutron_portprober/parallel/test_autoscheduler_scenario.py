import pytest
import time

from openstack_controller.tests.functional.exporter import (
    base as exporter_base,
)
from openstack_controller.tests.functional.neutron_portprober import base
from openstack_controller.tests.functional import config
from openstack_controller.tests.functional import waiters

CONF = config.Config()


@pytest.mark.xdist_group("exporter-compute-network")
class AutoschedulerTestCase(
    base.BaseFunctionalPortProberTestCase, exporter_base.PrometheusMixin
):

    def test_agents_present(self):
        agents = len(self.get_portprober_agent())
        self.assertEqual(
            agents > 0, True, "The number of portprober agents is not correct."
        )

    def _test_network_sits_on_agents(self, network_id, expected_number):
        agents = self.get_agents_hosting_portprober_network(network_id)
        self.assertEqual(
            len(agents),
            expected_number,
            f"The network {network_id} binding to agent is not correct.",
        )

    def _check_arping_metrics_for_port(self, port):
        self._check_arping_metrics_for_network(port["network_id"])
        agents = self.get_agents_hosting_portprober_network(port["network_id"])
        for agent in agents:
            exporter_url = self.get_exporter_url(agent["host"])
            agent_metric_families = list(
                self.get_metric_families(exporter_url)
            )
            for metric in ["failure", "success", "total"]:
                metric_name = f"portprober_arping_target_{metric}"
                m = self.get_metric(metric_name, agent_metric_families)
                samples = self.filter_metric_samples(
                    m, {"mac": port.mac_address}
                )
                self.assertTrue(
                    len(samples) == 1,
                    f"Did not find {metric_name} for port mac {port.mac_address}",
                )

    def _get_arping_agent_samples(self, port):
        agent_samples = {"total": {}, "success": {}, "failure": {}}
        for metric in agent_samples.keys():
            agent_samples[metric] = self.get_arping_samples_for_port(
                port, metric
            )
        return agent_samples

    def _check_arping_sample_value_rates_port(self, port, host_up=True):
        before = self._get_arping_agent_samples(port)
        time.sleep(CONF.PORTPROBER_PROBE_INTERVAL)
        after = self._get_arping_agent_samples(port)

        for agent in before["total"].keys():
            self.assertTrue(
                before["total"][agent][0].value
                < after["total"][agent][0].value,
                f"The total value not increased on agent {agent}.",
            )
            if host_up:
                self.assertTrue(
                    before["success"][agent][0].value
                    < after["success"][agent][0].value,
                    f"The success metric is not increased on agent {agent}.",
                )
                self.assertTrue(
                    before["failure"][agent][0].value
                    == after["failure"][agent][0].value,
                    f"The failure metric was changed on agent {agent}.",
                )
            else:
                self.assertTrue(
                    before["failure"][agent][0].value
                    < after["failure"][agent][0].value,
                    f"The failure metric is not increased on agent {agent}.",
                )
                self.assertTrue(
                    before["success"][agent][0].value
                    == after["success"][agent][0].value,
                    f"The success metric was changed on agent {agent}.",
                )

    def test_portprober_autoscheduler(self):
        net = self.network_create()
        self._test_network_sits_on_agents(net["id"], 0)
        self.subnet_create(cidr=CONF.TEST_SUBNET_RANGE, network_id=net["id"])
        # TODO(vsaienko): handle fast network create/delete when portprober did not setup
        # its port but network is deleted.
        time.sleep(1)
        self._test_network_sits_on_agents(
            net["id"], CONF.PORTPROBER_AGENTS_PER_NETWORK
        )

    def test_server_basic_ops(self):
        bundle = self.network_bundle_create()
        subnet = bundle["subnet"]
        network = bundle["network"]
        fixed_ips = [{"subnet_id": subnet["id"]}]
        port = self.port_create(network["id"], fixed_ips=fixed_ips)
        server = self.server_create(networks=[{"port": port.id}])
        self.wait_arping_samples_for_port(
            port, CONF.PORTPROBER_METRIC_REFRESH_TIMEOUT, 5
        )
        self._test_network_sits_on_agents(
            network["id"], expected_number=CONF.PORTPROBER_AGENTS_PER_NETWORK
        )
        self._check_arping_metrics_for_port(port)
        self._check_arping_sample_value_rates_port(port, host_up=True)
        self.ocm.oc.compute.stop_server(server)
        waiters.wait_for_server_status(self.ocm, server, "SHUTOFF")
        time.sleep(CONF.PORTPROBER_PROBE_INTERVAL)
        self._check_arping_sample_value_rates_port(port, host_up=False)
        # TODO(vsaienko): add a case when port is deleted and metrics
        # should disappear
