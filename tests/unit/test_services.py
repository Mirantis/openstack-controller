import copy
import logging
from unittest import mock

from openstack_controller import secrets
from openstack_controller import services


@mock.patch.object(services.Keystone, "template_args")
@mock.patch.object(services.base.Service, "_get_osdpl")
def test_service_keystone_render(
    mock_osdpl, mock_template_args, openstackdeployment, kubeapi
):
    class MockOsdpl:
        metadata = {"generation": 123}

    creds = secrets.OSSytemCreds("test", "test")
    admin_creds = secrets.OpenStackAdminCredentials(creds, creds, creds)
    creds_dict = {"user": creds, "admin": creds}
    credentials = secrets.OpenStackCredentials(
        database=creds_dict,
        messaging=creds_dict,
        notifications=creds_dict,
        memcached="secret",
    )
    service_creds = [secrets.OSServiceCreds("test", "test", "test")]

    mock_osdpl.return_value = MockOsdpl()
    mock_template_args.return_value = {
        "credentials": credentials,
        "admin_creds": admin_creds,
        "service_creds": service_creds,
    }
    openstackdeployment_old = copy.deepcopy(openstackdeployment)
    service = services.Keystone(openstackdeployment, logging)
    identity_helmbundle = service.render()
    # check no modification in-place for openstackdeployment
    assert openstackdeployment_old == openstackdeployment
    assert identity_helmbundle["metadata"]["name"] == "openstack-identity"
    # check helmbundle has data from base.yaml
    assert identity_helmbundle["spec"]["releases"][0]["values"]["images"][
        "tags"
    ]
