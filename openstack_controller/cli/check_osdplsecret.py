#!/usr/bin/env python3
from openstack_controller import kube
from openstack_controller import settings

import logging
import sys

namespace = settings.OSCTL_OS_DEPLOYMENT_NAMESPACE

logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
LOG = logging.getLogger(__name__)


def main():
    osdplsecrets = list(
        kube.OpenStackDeploymentSecret.objects(kube.kube_client()).filter(
            namespace=namespace
        )
    )
    if len(osdplsecrets) != 0:
        LOG.error(
            f"The OpenStackDeploymentSecret object exists, but is deprecated and removed. Current osdplsecrets: {osdplsecrets}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()