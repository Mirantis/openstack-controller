import logging
import sys

import yaml

from osh_operator import layers


def main(args):
    n = len(args)
    openstackdeployment_file = "examples/stein/core-ceph.yaml"
    openstackdeployment = yaml.safe_load(open(openstackdeployment_file))
    base = yaml.safe_load(layers.ENV.get_template(f"stein/base.yaml").render())
    openstackdeployment["spec"] = layers.merger.merge(
        base, openstackdeployment["spec"]
    )
    openstackdeployment["spec"]["features"]["ssl"]["public_endpoints"][
        "enabled"
    ] = False

    if n == 1:
        print(yaml.dump(openstackdeployment))
    else:
        service = args[1]
        template_only = args[2:3]
        func = (
            layers.render_service_template
            if template_only
            else layers.render_all
        )
        if template_only:
            openstackdeployment["spec"]["common"] = {
                "infra": {},
                "openstack": {"repo": ""},
            }
        print(
            yaml.dump(
                func(
                    service,
                    openstackdeployment,
                    openstackdeployment["metadata"],
                    openstackdeployment["spec"],
                    logging,
                )
            )
        )


if __name__ == "__main__":
    main(sys.argv)
