import pytest
from unittest import mock

from openstack_controller import constants
from openstack_controller.controllers import health


@pytest.mark.asyncio
async def test_hook_called():
    meta = {
        "name": "nova-compute-default",
        "labels": {"application": "nova", "component": "compute"},
    }
    compute_ds_name = meta["name"]
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
            "health": {"nova": {"compute-default": {"status": constants.BAD}}}
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

    def fake_hook(osdpl, namespace, meta, status, **kwargs):
        raise ValueError("fake-hook-test")

    # failed to patch as function decorator probably due to asynio decorator
    # so let's patch with the context manager
    with mock.patch("openstack_controller.kube.get_osdpl") as o, mock.patch(
        "kopf.adopt"
    ), mock.patch("openstack_controller.kube.resource"), mock.patch(
        "openstack_controller.kube.find"
    ) as find:
        find.return_value.obj = cronjob
        o.return_value.obj = osdpl
        ds_hooks = health.DAEMONSET_HOOKS[(constants.BAD, constants.OK)]
        # make sure mapping is correct
        assert compute_ds_name in ds_hooks
        ds_hooks[compute_ds_name] = fake_hook
        with pytest.raises(ValueError, match="^fake-hook-test$"):
            await health.daemonsets(
                compute_ds_name,
                "openstack",
                meta,
                status,
                "",
                body={"status": status},
                new={"desiredNumberScheduled": 2},
            )
