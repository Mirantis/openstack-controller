import logging
import requests
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

    fed_auth = {
        "os_auth_type": "v3oidcpassword",
        "os_identity_provider": "keycloak",
        "os_protocol": "mapped",
        "os_openid_scope": "openid",
        "os_password": f"{writer_password}",
        "os_project_domain_name": "Default",
        "os_project_name": "admin",
        "os_discovery_endpoint": f"https://{keycloak_ip}/auth/realms/iam/.well-known/openid-configuration",
        "os_auth_url": "http://keystone-api.openstack.svc.cluster.local:5000/v3",
        "os_insecure": True,
        "os_client_secret": "NotNeeded",
        "os_client_id": "os",
        "os_username": "writer",
        "os_interface": "internal",
        "os_endpoint_type": "internal",
        "api_timeout": 60,
    }

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
        fed = openstack.connect(load_yaml_config=False, **self.fed_auth)
        fed.authorize()
        assert (
            len(list(fed.network.networks())) > 0
        ), "List of networks is empty"

        assert (
            self.fed_auth["os_username"]
            == fed.identity.get_user(fed.current_user_id).name
        ), "User name doesn't match"

        assert (
            self.fed_auth["os_project_name"]
            == fed.identity.get_project(fed.current_project_id).name
        ), "Project name doesn't match"

    def test_keystone_keycloak_integration_req(self):
        verify = None

        if self.fed_auth.get("os_cacert"):
            verify = self.fed_auth["os_cacert"]
        elif self.fed_auth.get("os_insecure") is True:
            verify = False

        timeout = self.fed_auth.get("api_timeout", 60)

        discovery_resp = requests.get(
            self.fed_auth["os_discovery_endpoint"],
            verify=verify,
            timeout=timeout,
        )

        token_endpoint = discovery_resp.json()["token_endpoint"]
        access_req_data = (
            "username={os_username}&password={os_password}&scope={os_openid_scope}&grant_type"
            "=password"
        ).format(**self.fed_auth)

        access_resp = requests.post(
            token_endpoint,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=access_req_data,
            auth=(
                self.fed_auth["os_client_id"],
                self.fed_auth["os_client_secret"],
            ),
            verify=verify,
            timeout=timeout,
        )

        access_token = access_resp.json()["access_token"]

        unscoped_token_resp = requests.post(
            "{os_auth_url}/OS-FEDERATION/identity_providers/{os_identity_provider}/protocols/{os_protocol}/auth".format(
                **self.fed_auth
            ),
            headers={"Authorization": f"Bearer {access_token}"},
            verify=verify,
            timeout=timeout,
        )

        unscoped_token = unscoped_token_resp.headers.get("x-subject-token")

        scoped_auth_req = {
            "auth": {
                "identity": {
                    "methods": ["token"],
                    "token": {"id": unscoped_token},
                },
                "scope": {
                    "project": {
                        "domain": {
                            "name": self.fed_auth["os_project_domain_name"]
                        },
                        "name": self.fed_auth["os_project_name"],
                    }
                },
            }
        }

        scoped_token_resp = requests.post(
            "{os_auth_url}/auth/tokens".format(**self.fed_auth),
            headers={"Content-Type": "application/json"},
            json=scoped_auth_req,
            verify=verify,
            timeout=timeout,
        )

        # more info on user, its roles and groups is in the JSON body of the response
        scoped_token = scoped_token_resp.headers.get("x-subject-token")

        catalog = scoped_token_resp.json()["token"]["catalog"]
        interface = self.fed_auth.get("os_interface", "public")

        network_service = [s for s in catalog if s["type"] == "network"]
        if network_service:
            network_service = network_service[0]
        else:
            raise Exception("Could not find network service in catalog")

        network_api = [
            e["url"]
            for e in network_service["endpoints"]
            if e["interface"] == interface
        ]

        if network_api:
            network_api = network_api[0]
            if not network_api.rstrip("/").endswith("/v2.0"):
                network_api = network_api.rstrip("/") + "/v2.0"
        else:
            raise Exception(
                "Could not find required endpoint for network service"
            )

        networks_resp = requests.get(
            f"{network_api}/networks",
            headers={"X-Auth-Token": scoped_token},
            verify=verify,
            timeout=timeout,
        )

        assert (
            networks_resp.status_code == requests.codes.ok
        ), f"GET /networks response is not OK {networks_resp.status_code}"
        assert (
            len(networks_resp.json()["networks"]) > 0
        ), f"GET /networks response was {networks_resp.text}"
