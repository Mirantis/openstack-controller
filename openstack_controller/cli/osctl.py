#!/usr/bin/env python3
import asyncio
import argparse
import sys
import time

from openstack_controller import kube
from openstack_controller import utils
from openstack_controller import osdplstatus
from openstack_controller import health

LOG = utils.get_logger(__name__)

OSDPL_NAMESPACE = "openstack"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Client to manage OpenStackDeployment resource."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    credentials_parser = subparsers.add_parser(
        "credentials", help="Supported subcommands: rotate"
    )
    credentials_sub = credentials_parser.add_subparsers(
        dest="credentials_subcommand", required=True
    )

    rotation_parser = credentials_sub.add_parser(
        "rotate", help="Trigger openstack deployment credentials rotation"
    )
    rotation_parser.add_argument(
        "--osdpl",
        required=True,
        type=str,
        help="Name of OpenstackDeployment object",
    )
    rotation_parser.add_argument(
        "--namespace",
        default=OSDPL_NAMESPACE,
        type=str,
        help="Name of OpenstackDeployment object namespace",
    )
    rotation_parser.add_argument(
        "--type",
        required=True,
        action="append",
        choices=["admin", "service"],
        help="""Type of credentials to rotate.
                Use `admin` to rotate admin credentials for keystone.
                Use `service` to rotate  mysql/rabbitmq/keystone credentials. Can be specified multiple time.""",
    )
    rotation_parser.add_argument(
        "--wait", required=False, default=False, action="store_true"
    )

    return parser.parse_args()


def main():
    args = parse_args()
    creds_groups = set(args.type)

    osdpl = kube.find(
        kube.OpenStackDeployment, args.osdpl, args.namespace, silent=True
    )
    if not osdpl:
        LOG.error(
            f"The OpenStackDeployment {args.namespace}/{args.osdpl} was not found!"
        )
        sys.exit(1)
    osdpl.reload()

    rotation_id = {}
    for creds_group in creds_groups:
        rotation_id[creds_group] = (
            utils.get_in(
                osdpl.obj,
                ["status", "credentials", creds_group, "rotation_id"],
                0,
            )
            + 1
        )

    LOG.info(f"Starting rotation for {creds_groups}")
    patch = {
        "status": {
            "credentials": {
                creds_group: {"rotation_id": rotation_id[creds_group]}
                for creds_group in creds_groups
            }
        }
    }
    osdplst = osdplstatus.OpenStackDeploymentStatus(args.osdpl, args.namespace)

    osdpl.patch(patch, subresource="status")
    LOG.info(
        f"Started credential rotation for {creds_groups}, please wait for OpenstackDeployment status becoming APPLIED."
    )

    if args.wait is True:
        LOG.info(f"Waiting rotation changes are applied")
        osdplst = osdplstatus.OpenStackDeploymentStatus(
            args.osdpl, args.namespace
        )
        loop = asyncio.get_event_loop()
        while True:
            if osdplst.get_osdpl_status() == osdplstatus.APPLYING:
                break
            time.sleep(10)
        while True:
            if osdplst.get_osdpl_status() == osdplstatus.APPLIED:
                LOG.info(f"Waiting openstack services are healty.")
                if loop.run_until_complete(
                    health.wait_services_healthy(osdpl.mspec, osdplst)
                ):
                    break
            time.sleep(10)


if __name__ == "__main__":
    main()
