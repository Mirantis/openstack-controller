import copy
import logging
from unittest import mock

from openstack_controller import services


@mock.patch.object(services.base.Service, "_get_osdpl")
def test_service_keystone_render(
    mock_osdpl, openstackdeployment, kubeapi, credentials, service_credentials
):
    class MockOsdpl:
        metadata = {"generation": 123}

    mock_osdpl.return_value = MockOsdpl()
    openstackdeployment_old = copy.deepcopy(openstackdeployment)
    service = services.Keystone(openstackdeployment, logging)
    compute_helmbundle = service.render()
    # check no modification in-place for openstackdeployment
    assert openstackdeployment_old == openstackdeployment
    assert compute_helmbundle["metadata"]["name"] == "openstack-identity"
    # check helmbundle has data from base.yaml
    assert compute_helmbundle["spec"]["releases"][0]["values"]["images"][
        "tags"
    ]
