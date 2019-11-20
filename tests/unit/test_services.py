import copy
import logging

from openstack_controller import services


def test_service_keystone_render(
    openstackdeployment, kubeapi, credentials, service_credentials
):
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
