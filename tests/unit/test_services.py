import copy
import logging

from osh_operator import services


def test_service_nova_render(openstackdeployment, kubeapi, credentials):
    # creds = {"messaging": {"user": {"username": "spam", "password": "ham"}},
    #          "database": {"user": {"username": "eggs", "password": "parrot"}}
    #          }
    # credentials.return_value = creds

    openstackdeployment_old = copy.deepcopy(openstackdeployment)
    service = services.Nova(openstackdeployment, logging)
    compute_helmbundle = service.render()
    # check no modification in-place for openstackdeployment
    assert openstackdeployment_old == openstackdeployment
    assert compute_helmbundle["metadata"]["name"] == "openstack-compute"
    # check helmbundle has data from base.yaml
    assert compute_helmbundle["spec"]["releases"][0]["values"]["images"][
        "tags"
    ]
