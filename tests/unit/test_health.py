import pytest
from unittest import mock

from openstack_controller import constants
from openstack_controller.controllers import health


@pytest.mark.asyncio
async def test_hook_called():
    meta = {"name": "nova-compute-default"}
    status = {
        "currentNumberScheduled": 1,
        "desiredNumberScheduled": 1,
        "numberReady": 1,
        "updatedNumberScheduled": 1,
        "numberAvailable": 1,
        "numberMisscheduled": 0,
        "observedGeneration": 1,
    }
    osdpl = {
        "name": "fake-name",
        "status": {
            "nova-compute-default": {
                "nova-compute-default": {"status": constants.PROGRESS}
            }
        },
        "spec": {
            "openstack_version": "master",
            "artifacts": {"images_base_url": "", "binary_base_url": ""},
        },
    }

    cronjob = {
        "metadata": {"annotations": ""},
        "spec": {
            "jobTemplate": {
                "metadata": {"labels": ""},
                "spec": {
                    "template": {
                        "spec": {"containers": [{"name": "nova-cell-setup"}]},
                    }
                },
            }
        },
    }

    def fake_hook(osdpl, namespace, meta, status):
        assert osdpl.obj["name"] == "fake-name"

    # failed to patch as function decorator probably due to asynio decorator
    # so let's patch with the context manager
    with mock.patch("openstack_controller.health.get_osdpl") as o, mock.patch(
        "kopf.adopt"
    ), mock.patch("openstack_controller.kube.resource"), mock.patch(
        "openstack_controller.kube.find"
    ) as find:
        find.return_value.obj = cronjob
        o.return_value.obj = osdpl
        await health.daemonsets(
            meta["name"],
            "openstack",
            meta,
            status,
            "",
            body={"status": status},
        )
        health.DAEMONSET_HOOKS = {
            (constants.PROGRESS, constants.OK): {
                "nova-compute-default": fake_hook
            },
        }
        await health.daemonsets(
            meta["name"],
            "openstack",
            meta,
            status,
            "",
            body={"status": status},
        )
