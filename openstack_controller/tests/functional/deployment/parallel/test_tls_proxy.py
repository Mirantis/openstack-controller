import re
import unittest

from openstack_controller.tests.functional import base
from openstack_controller import settings
from openstack_controller import kube


class TlsProxyFunctionalTestCase(base.BaseFunctionalTestCase):
    def setUp(self):
        super().setUp()
        if (
            not self.osdpl.obj["spec"]["features"]
            .get("ssl", {})
            .get("tls_proxy", {})
            .get("enabled", True)
        ):
            raise unittest.SkipTest("TLS proxy not enabled.")

    @property
    def ingress_pods(self):
        kube_api = kube.kube_client()
        return kube.Pod.objects(kube_api).filter(
            namespace=settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
            selector={"application": "ingress", "component": "server"},
        )

    def test_tls_proxy_deployed(self):
        pod = next(self.ingress_pods.iterator())
        for container in pod.obj["spec"]["containers"]:
            if container["name"] == "tls-proxy":
                return
        assert False, "Did not found tls-proxy container in containers."

    def test_fips_mode_activated(self):
        pod = next(self.ingress_pods.iterator())
        proxy_info = (
            pod.exec(
                command=["tls-proxy", "--version"], container="tls-proxy"
            )["stderr"]
            .split("\n")[0]
            .lower()
        )
        res = re.search(r".*fips\s\[.*enabled\s*=\s*(\w+),\s*.*]", proxy_info)
        if res is None:
            assert False, "FIPS not activated for TLS-proxy."
        else:
            assert (
                res.group(len(res.groups())) == "true"
            ), "FIPS not activated for TLS-proxy."
