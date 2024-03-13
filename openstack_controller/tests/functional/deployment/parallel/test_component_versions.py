from parameterized import parameterized
from openstack_controller.tests.functional import base
from openstack_controller import settings
from openstack_controller import kube


class ComponentVersionsFunctionalTestCase(base.BaseFunctionalTestCase):
    def setUp(self):
        super().setUp()
        self.check_scheme = {
            "ceph": [
                {
                    "pkg_names": ["ceph-common"],
                    "pkg_type": "dpkg",
                    "check_pods": [
                        {
                            "application": "libvirt",
                            "component": "libvirt",
                            "container": "libvirt",
                        },
                        {
                            "application": "cinder",
                            "component": "volume",
                            "container": "cinder-volume",
                        },
                        {
                            "application": "glance",
                            "component": "api",
                            "container": "glance-api",
                        },
                        {
                            "application": "nova",
                            "component": "compute",
                            "container": "nova-compute",
                        },
                        {
                            "application": "manila",
                            "component": "api",
                            "container": "manila-api",
                        },
                    ],
                }
            ],
        }

    def _get_command_line(self, pkg_type, pkg_name):
        if pkg_type == "pip":
            command = ["pip", "show", pkg_name]
        elif pkg_type == "dpkg":
            command = ["dpkg", "-s", pkg_name]
        else:
            assert False, f"Unsupported version type: {pkg_type}"
        return command

    @parameterized.expand(
        [
            ("ceph"),
        ]
    )
    def test_check_version_are_same(self, scheme_name):
        kube_api = kube.kube_client()
        have_different_version = {}
        scheme = self.check_scheme[scheme_name][0]
        for pkg_name in scheme["pkg_names"]:
            versions = {}
            command = self._get_command_line(scheme["pkg_type"], pkg_name)
            for check_pod in scheme["check_pods"]:
                pods = kube.Pod.objects(kube_api).filter(
                    namespace=settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
                    selector={
                        "application": check_pod["application"],
                        "component": check_pod["component"],
                    },
                )
                pods = [pod for pod in pods]
                if not pods:
                    continue
                pod = pods[0]
                version = pod.exec(command, container=check_pod["container"])[
                    "stdout"
                ]
                self.assertTrue(
                    version
                ), f"Failed to get version of {pkg_name} in pod: {check_pod}"
                versions[pod] = version
            self.assertTrue(
                versions
            ), f"Failed to get version of {pkg_name} in pods: {scheme['check_pods']}"
            if len(set(versions.values())) != 1:
                have_different_version[pkg_name] = versions
        self.assertFalse(
            have_different_version
        ), f"Packages have different version: {have_different_version}"
