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

    def _check_arping_metrics_for_port(self, port, present=True):
        agents = self.get_agents_hosting_portprober_network(port["network_id"])
        # NOTE(vsaienko): if port does not exists, other ports may not exists
        # And whole metric set is empty.
        if present:
            self._check_arping_metrics_for_network(port["network_id"])
        expected_samples = 1
        if present is False:
            expected_samples = 0
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
                    len(samples) == expected_samples,
                    f"Did not find {metric_name} for port mac {port.mac_address}",
                )

    def _get_arping_agent_samples(self, port):
        agent_samples = {"total": {}, "success": {}, "failure": {}}
        for metric in agent_samples.keys():
            agent_samples[metric] = self.get_arping_samples_for_port(
                port, metric
            )
        return agent_samples

    def _wait_metric_incresing(self, port, metric, timeout):
        start_time = int(time.time())
        before = self._get_arping_agent_samples(port)
        while True:
            timed_out = int(time.time()) - start_time
            if timed_out >= timeout:
                message = f"Metric {metric} for port {port.id} is not changed during {timeout}."
                raise TimeoutError(message)
            after = self._get_arping_agent_samples(port)
            agent_increased = []
            for agent in before["total"].keys():
                if (
                    before[metric][agent][0].value
                    < after[metric][agent][0].value
                ):
                    agent_increased.append(agent)
            if set(agent_increased) == set(before["total"].keys()):
                return

    def _check_arping_sample_value_rates_port(self, port, host_up=True):
        before = self._get_arping_agent_samples(port)
        time.sleep(CONF.PORTPROBER_PROBE_INTERVAL)
        after = self._get_arping_agent_samples(port)

        for agent in before["total"].keys():
            self.assertTrue(
                before["total"][agent][0].value
                < after["total"][agent][0].value,
                f"The total value not increased on agent {agent} with host_up {host_up}.",
            )
            if host_up:
                self.assertTrue(
                    before["success"][agent][0].value
                    < after["success"][agent][0].value,
                    f"The success metric is not increased on agent {agent} with host_up {host_up}.",
                )
                self.assertTrue(
                    before["failure"][agent][0].value
                    == after["failure"][agent][0].value,
                    f"The failure metric was changed on agent {agent} with host_up {host_up}.",
                )
            else:
                self.assertTrue(
                    before["failure"][agent][0].value
                    < after["failure"][agent][0].value,
                    f"The failure metric is not increased on agent {agent} with host_up {host_up}.",
                )
                self.assertTrue(
                    before["success"][agent][0].value
                    == after["success"][agent][0].value,
                    f"The success metric was changed on agent {agent} with host_up {host_up}.",
                )

    def test_portprober_autoscheduler_ipv4(self):
        net = self.network_create()
        self._test_network_sits_on_agents(net["id"], 0)
        self.subnet_create(cidr=CONF.TEST_SUBNET_RANGE, network_id=net["id"])
        # TODO(vsaienko): handle fast network create/delete when portprober did not setup
        # its port but network is deleted.
        time.sleep(1)
        self._test_network_sits_on_agents(
            net["id"], CONF.PORTPROBER_AGENTS_PER_NETWORK
        )

    def test_portprober_autoscheduler_ipv6(self):
        net = self.network_create()
        self._test_network_sits_on_agents(net["id"], 0)
        self.subnet_create(
            cidr=CONF.TEST_IPV6_SUBNET_RANGE,
            ip_version=6,
            network_id=net["id"],
        )
        # TODO(vsaienko): handle fast network create/delete when portprober did not setup
        # its port but network is deleted.
        time.sleep(1)
        self._test_network_sits_on_agents(
            net["id"], CONF.PORTPROBER_AGENTS_PER_NETWORK
        )

    def _test_server_basic_ops(self, network, port, image=None, flavor=None):
        server = self.server_create(
            imageRef=image,
            networks=[{"port": port.id}],
            config_drive=True,
            flavorRef=flavor,
        )
        self.wait_arping_samples_for_port(
            port, CONF.PORTPROBER_METRIC_REFRESH_TIMEOUT, 5
        )
        self._test_network_sits_on_agents(
            network["id"],
            expected_number=CONF.PORTPROBER_AGENTS_PER_NETWORK,
        )
        self._check_arping_metrics_for_port(port)
        # NOTE(vsaienko): Ubuntu boots near 30 seconds, give more time
        # to check metric start increasing.
        self._wait_metric_incresing(
            port,
            "success",
            CONF.PORTPROBER_PROBE_INTERVAL
            + CONF.PORTPROBER_METRIC_REFRESH_TIMEOUT,
        )
        self._check_arping_sample_value_rates_port(port, host_up=True)
        self.ocm.oc.compute.stop_server(server)
        waiters.wait_for_server_status(self.ocm, server, "SHUTOFF")
        self._wait_metric_incresing(
            port, "failure", CONF.PORTPROBER_PROBE_INTERVAL
        )
        self._check_arping_sample_value_rates_port(port, host_up=False)
        self.server_delete(server)
        time.sleep(CONF.PORTPROBER_METRIC_REFRESH_TIMEOUT)
        self._check_arping_metrics_for_port(port, present=False)

    # TODO(vsaienko): add basic ops with ipv6 when is is implemented
    def test_server_basic_ops_ipv4_private(self):
        bundle = self.network_bundle_create()
        subnet = bundle["subnet"]
        network = bundle["network"]
        fixed_ips = [{"subnet_id": subnet["id"]}]
        port = self.port_create(network["id"], fixed_ips=fixed_ips)
        self._test_server_basic_ops(network, port)

    def test_server_basic_ops_direct_fip(self):
        public_net = list(
            self.ocm.oc.network.networks(name=CONF.PUBLIC_NETWORK_NAME)
        )[0]
        subnet = self.ocm.oc.network.get_subnet(public_net["subnets"][0])
        fixed_ips = [{"subnet_id": subnet["id"]}]
        port = self.port_create(public_net["id"], fixed_ips=fixed_ips)
        image = self.ocm.oc.get_image_id(CONF.UBUNTU_TEST_IMAGE_NAME)
        flavor = self.ocm.oc.compute.find_flavor(
            CONF.TEST_FLAVOR_SMALL_NAME
        ).id
        self._test_server_basic_ops(public_net, port, image, flavor=flavor)