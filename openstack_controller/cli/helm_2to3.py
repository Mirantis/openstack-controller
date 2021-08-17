#!/usr/bin/env python3
import asyncio
import os
import sys

from openstack_controller import kube
from openstack_controller import settings
from openstack_controller import services
from openstack_controller import utils
from openstack_controller.helm import HelmManager

TILLER_NAMESPACE = os.environ.get("TILLER_NAMESPACE", "stacklight")
RELEASE_STORAGE = os.environ.get("RELEASE_STORAGE", "configmaps")
RELEASE_VERSION_MAX = int(os.environ.get("RELEASE_VERSION_MAX", 3))
HELMBUNDLE_NAMESPACE = os.environ.get(
    "HELMBUNDLE_NAMESPACE", settings.OSCTL_OS_DEPLOYMENT_NAMESPACE
)
HELM2_CONTROLLER_DEPLOYMENT_NAME = os.environ.get(
    "HELM2_CONTROLLER_DEPLOYMENT_NAME", "stacklight-helm-controller"
)

LOG = utils.get_logger("osctl-2to3")


class HelmManager2to3(HelmManager):
    async def convert_2to3(
        self, name, release_storage=RELEASE_STORAGE, args=None
    ):
        args = args or []
        cmd = [
            "2to3",
            "convert",
            "--tiller-ns",
            self.namespace,
            "--tiller-out-cluster",
            "--release-storage",
            release_storage,
            "--release-versions-max",
            self.max_history,
            name,
            *args,
        ]
        stdout, stderr = await self.run_cmd(cmd)
        return (stdout, stderr)

    async def cleanup_2to3(
        self, name, release_storage=RELEASE_STORAGE, args=None
    ):
        args = args or []
        cmd = [
            "2to3",
            "cleanup",
            "--tiller-ns",
            self.namespace,
            "--tiller-out-cluster",
            "--release-storage",
            release_storage,
            "--release-cleanup",
            "--skip-confirmation",
            "--name",
            name,
            *args,
        ]
        stdout, stderr = await self.run_cmd(cmd)
        return (stdout, stderr)


async def _main():
    helm_manager = HelmManager2to3(
        namespace=TILLER_NAMESPACE, history_max=RELEASE_VERSION_MAX
    )

    has_errors = False

    osdpl_helmbundles = [
        f"openstack-{x}" for x in services.registry.keys() if x is not None
    ]

    helm2_deployment = None
    helm2_need_to_scale = False

    for hb_name in osdpl_helmbundles:
        hb = kube.find(
            kube.HelmBundle,
            name=hb_name,
            namespace=HELMBUNDLE_NAMESPACE,
            silent=True,
        )
        if hb and hb.exists():
            LOG.info(
                "Found at least one helmbundle. Need to scale helm2 controller."
            )
            helm2_need_to_scale = True
            break

    if helm2_need_to_scale:
        LOG.info(
            "Looking for SL controller deployment {HELM2_CONTROLLER_DEPLOYMENT_NAME}"
        )
        helm2_deployment = kube.find(
            kube.Deployment,
            HELM2_CONTROLLER_DEPLOYMENT_NAME,
            namespace=TILLER_NAMESPACE,
            silent=True,
            cluster=False,
        )
        if helm2_deployment:
            LOG.info("Scaling helm2 controller deployment to 0")
            helm2_deployment.scale(replicas=0)
            await helm2_deployment.wait_for_replicas(0)
        else:
            LOG.warning(
                "SL helm controller deployment not found. Skipping scale."
            )

    for hb_name in osdpl_helmbundles:
        hb = kube.find(
            kube.HelmBundle,
            name=hb_name,
            namespace=HELMBUNDLE_NAMESPACE,
            silent=True,
        )
        if hb is None or not hb.exists():
            LOG.info(
                f"The helmbundle {hb_name} does not exist, skipping migration."
            )
            continue

        hb.reload()
        hb.obj["spec"]["releases"]
        failed_releases = []
        for release in hb.obj["spec"]["releases"]:
            release_name = release["name"]
            try:
                LOG.info(f"Converting release {release_name}")
                stdout, stderr = await helm_manager.convert_2to3(release_name)
                LOG.info(
                    f"Converted release {release_name}. stdout: {stdout}, stderr: {stderr}"
                )
                LOG.info(f"Removing release {release_name}")
                stdout, stderr = await helm_manager.cleanup_2to3(release_name)
                LOG.info(
                    f"Removed release {release_name}. stdout: {stdout}, stderr: {stderr}"
                )
                LOG.info(f"The release {release_name} removed successfully.")
            except Exception:
                failed_releases.append(release_name)
                LOG.error(f"Failed to convert/cleanup helmv2 release.")

        if failed_releases:
            LOG.error(f"Skipping helmbundle {hb_name} removal.")
            LOG.error(
                f"Failed to remove {failed_releases} for helmbundle {hb_name}"
            )
            has_errors = True
        else:
            LOG.info(f"Removing release {release_name}")
            hb.delete(propagation_policy="Foreground")
            # NOTE(vsaienko): allow helmbundle to be removed immidiately.
            hb.patch({"metadata": {"finalizers": []}})
            await kube.wait_for_deleted(hb, times=60, seconds=10)
            LOG.info(f"The helmbundle {hb.name} removed successfully.")

    if has_errors:
        LOG.error(
            "Got errors while trying to convert releases. Please inspect logs above."
        )
        sys.exit(1)

    if helm2_deployment:
        LOG.info("Scaling helm2 controller deployment to 3")
        helm2_deployment.reload()
        helm2_deployment.scale(replicas=3)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())
