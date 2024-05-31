import logging
import unittest

import openstack

from openstack_controller.tests.functional import base, config
from openstack_controller import settings
from openstack_controller import kube

LOG = logging.getLogger(__name__)
CONF = config.Config()


class TestKeystoneIamIntegration(base.BaseFunctionalTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if (
            not cls.osdpl.obj["spec"]["features"]
            .get("keystone", {})
            .get("keycloak", {})
            .get("enabled", False)
        ):
            raise unittest.SkipTest("Keycloak is not enabled.")

        if not all(
            (
                CONF.OSDPL_IAM_KEYCLOAK_USER_WRITER_PWD,
                CONF.OSDPL_IAM_KEYCLOAK_IP,
            )
        ):
            raise unittest.SkipTest("Keycloak env vars are not set.")

    keycloak_ip = CONF.OSDPL_IAM_KEYCLOAK_IP
    writer_password = CONF.OSDPL_IAM_KEYCLOAK_USER_WRITER_PWD

    def test_keystone_keycloak_integration(self):
        kube_api = kube.kube_client()
        pods = kube.Pod.objects(kube_api).filter(
            namespace=settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
            selector={"application": "keystone", "component": "client"},
        )
        assert len(pods) > 0, "POD <keystone-client-*> not found"
        keystone_pod = pods.query_cache["objects"][0]
        envs = (
            f"OS_CLIENT_SECRET=someRandomClientSecretMightBeNull "
            f"OS_PROJECT_DOMAIN_ID=default "
            f"OS_INTERFACE=public "
            f"OS_USERNAME=writer "
            f"OS_PASSWORD={self.writer_password} "
            f"OS_CACERT=/etc/ssl/certs/openstack-ca-bundle.pem "
            f"OS_AUTH_URL=http://keystone-api.openstack.svc.cluster.local:5000/v3 "
            f"OS_CLIENT_ID=os "
            f"OS_PROTOCOL=mapped "
            f"OS_IDENTITY_PROVIDER=keycloak "
            f"OS_DISCOVERY_ENDPOINT=https://{self.keycloak_ip}/"
            f"auth/realms/iam/.well-known/openid-configuration "
            f"OS_AUTH_TYPE=v3oidcpassword "
            f"OS_PROJECT_NAME=admin "
            f"OS_CLOUD="
        )
        error_msg = "===ERROR==="
        LOG.info(
            "\n",
            keystone_pod.exec(["/bin/bash", "-c", f"{envs} env|grep OS_"]),
        )
        server_list = keystone_pod.exec(
            [
                "/bin/bash",
                "-c",
                f"{envs} "
                f"openstack -vvv --insecure server list "
                f"|| echo '{error_msg}'",
            ]
        )
        if error_msg in server_list["stdout"]:
            raise Exception(f"\n{server_list}")

    def test_keystone_keycloak_integration_sdk(self):
        fed_auth = {
            "os_auth_type": "v3oidcpassword",
            "os_identity_provider": "keycloak",
            "os_protocol": "mapped",
            "os_openid_scope": "openid",
            "os_password": f"{self.writer_password}",
            "os_project_domain_name": "Default",
            "os_project_name": "admin",
            "os_discovery_endpoint": f"https://{self.keycloak_ip}/auth/realms/iam/.well-known/openid-configuration",
            "os_auth_url": "http://keystone-api.openstack.svc.cluster.local:5000/v3",
            "os_insecure": True,
            "os_client_secret": "NotNeeded",
            "os_client_id": "os",
            "os_username": "writer",
            "os_interface": "internal",
            "os_endpoint_type": "internal",
            "os_region_name": "RegionOne",
        }

        fed = openstack.connect(load_yaml_config=False, **fed_auth)
        fed.authorize()
        assert (
            len(list(fed.network.networks())) > 0
        ), "List of networks is empty"

        assert (
            fed_auth["os_username"]
            == fed.identity.get_user(fed.current_user_id).name
        ), "User name doesn't match"

        assert (
            fed_auth["os_project_name"]
            == fed.identity.get_project(fed.current_project_id).name
        ), "Project name doesn't match"
