#!/usr/bin/env python3
import argparse
import sys

from openstack_controller import kube
from openstack_controller import utils

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
        choices=["admin/identity"],
        help="""Type of credentials to rotate in format <creds_group>/<creds_name>.
                Currently only openstack administrator keystone account rotation is supported.""",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    creds_group, creds_name = args.type.split("/")

    osdpl = kube.find(
        kube.OpenStackDeployment, args.osdpl, args.namespace, silent=True
    )
    if not osdpl:
        LOG.error(
            f"The OpenStackDeployment {args.namespace}/{args.osdpl} was not found!"
        )
        sys.exit(1)
    osdpl.reload()

    current_rotation_id = utils.get_in(
        osdpl.obj,
        ["status", "credentials", creds_group, creds_name, "rotation_id"],
        0,
    )
    new_rotation_id = current_rotation_id + 1

    LOG.info(f"Starting rotation for {creds_group} {creds_name}")
    osdpl.patch(
        {
            "status": {
                "credentials": {
                    creds_group: {creds_name: {"rotation_id": new_rotation_id}}
                }
            }
        }
    )
    LOG.info(
        f"{creds_group} {creds_name} rotation has started, please wait for OpenstackDeployment status becoming applied"
    )


if __name__ == "__main__":
    main()
