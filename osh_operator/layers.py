import logging

import deepmerge
import jinja2
import yaml

from osh_operator.filters.tempest import generate_tempest_config
from . import openstack

LOG = logging.getLogger(__name__)

ENV = jinja2.Environment(
    loader=jinja2.PackageLoader(__name__.split(".")[0]),
    extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
)
LOG.info(f"found templates {ENV.list_templates()}")

ENV.filters["generate_tempest_config"] = generate_tempest_config

merger = deepmerge.Merger(
    # pass in a list of tuple, with the strategies you are looking to apply
    # to each type.
    # NOTE(pas-ha) We are handling results of yaml.safe_load and k8s api
    # exclusively, thus only standard json-compatible collection data types
    # will be present, so not botherting with collections.abc for now.
    [(list, ["append"]), (dict, ["merge"])],
    # next, choose the fallback strategies, applied to all other types:
    ["override"],
    # finally, choose the strategies in the case where the types conflict:
    # TODO(pas-ha) write own merger filter to FAIL merging of different types
    ["override"],
)

CHART_GROUP_MAPPING = {
    "openstack": [
        "cinder",
        "glance",
        "heat",
        "horizon",
        "keystone",
        "neutron",
        "nova",
        "octavia",
        "ceph-rgw",
        "designate",
    ],
    "infra": [
        "rabbitmq",
        "mariadb",
        "memcached",
        "openvswitch",
        "libvirt",
        "powerdns",
    ],
}


def services(spec, logger, event, **kwargs):
    to_apply = set(spec.get("features", {}).get("services", []))
    to_delete = {}
    # NOTE(pas-ha) each diff is (op, (path, parts, ...), old, new)
    # kopf ignores changes to status except its own internal fields
    # and metadata except labels and annotations
    # (kind and apiVersion and namespace are de-facto immutable)
    for op, path, old, new in kwargs.get("diff", []):
        logger.debug(f"{op} {'.'.join(path)} from {old} to {new}")
        if path == ("spec", "features", "services"):
            # NOTE(pas-ha) something changed in services,
            # need to check if any were deleted
            to_delete = set(old) - set(new)
    return to_apply, to_delete


def render_service_template(
    service, body, meta, spec, logger, **template_args
):
    os_release = spec["openstack_version"]
    # logger.debug(f"found templates {ENV.list_templates()}")
    tpl = ENV.get_template(f"{os_release}/{service}.yaml")
    logger.debug(f"Using template {tpl.filename}")

    text = tpl.render(body=body, meta=meta, spec=spec, **template_args)
    data = yaml.safe_load(text)
    return data


def merge_all_layers(service, body, meta, spec, logger, **template_args):

    data = render_service_template(
        service, body, meta, spec, logger, **template_args
    )

    # FIXME(pas-ha) either move to dict merging stage before,
    # or move to the templates themselves
    data["spec"]["repositories"] = spec["common"]["charts"]["repositories"]

    # We have 4 level of hierarchy:
    # 1. helm values.yaml - which is default
    # 2. osh-operator crd charts section
    # 3. osh-operator crd common/group section
    # 4. osh_operator/<openstack_version>/<chart>.yaml

    # The values are merged in this specific order.
    for release in data["spec"]["releases"]:
        chart_name = release["chart"].split("/")[-1]
        merger.merge(
            release, spec["common"].get("charts", {}).get("releases", {})
        )
        for group, charts in CHART_GROUP_MAPPING.items():
            if chart_name in charts:
                merger.merge(
                    release, spec["common"].get(group, {}).get("releases", {})
                )
                merger.merge(
                    release["values"],
                    spec["common"].get(group, {}).get("values", {}),
                )

        merger.merge(
            release["values"],
            spec.get("services", {})
            .get(service, {})
            .get(chart_name, {})
            .get("values", {}),
        )
    return data


def render_all(service, body, meta, spec, credentials, logger):
    # logger.debug(f"found templates {ENV.list_templates()}")
    os_release = spec["openstack_version"]
    tpl = ENV.get_template(f"{os_release}/{service}.yaml")
    profile = spec["profile"]
    logger.debug(f"Using profile {profile}")
    logger.debug(f"Using template {tpl.filename}")

    base = yaml.safe_load(
        ENV.get_template(f"{os_release}/{profile}.yaml").render()
    )
    # Merge operator defaults with user context.
    spec = merger.merge(base, spec)

    template_args = {}
    if service == "tempest":
        helmbundles_body = {}
        for s in set(spec["features"]["services"]) - set(["tempest"]):
            service_creds = openstack.get_or_create_os_credentials(
                s, meta["namespace"]
            )
            helmbundles_body[s] = merge_all_layers(
                s, body, meta, spec, logger, credentials=service_creds
            )
        template_args["helmbundles_body"] = helmbundles_body

    template_args["credentials"] = credentials

    data = merge_all_layers(service, body, meta, spec, logger, **template_args)

    return data
