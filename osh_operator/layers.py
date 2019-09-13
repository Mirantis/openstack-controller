import logging

import deepmerge
import deepmerge.exception
import deepmerge.strategy.type_conflict
import jinja2
import kopf
import yaml

from osh_operator.filters.tempest import generate_tempest_config

LOG = logging.getLogger(__name__)

ENV = jinja2.Environment(
    loader=jinja2.PackageLoader(__name__.split(".")[0]),
    extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
)
LOG.info(f"found templates {ENV.list_templates()}")

ENV.filters["generate_tempest_config"] = generate_tempest_config


class TypeConflictFail(
    deepmerge.strategy.type_conflict.TypeConflictStrategies
):
    @staticmethod
    def strategy_fail(config, path, base, nxt):
        raise deepmerge.exception.InvalidMerge(
            f"Trying to merge different types of objects, {type(base)} and "
            f"{type(nxt)}"
        )


class CustomMerger(deepmerge.Merger):
    def __init__(
        self, type_strategies, fallback_strategies, type_conflict_strategies
    ):
        super(CustomMerger, self).__init__(
            type_strategies, fallback_strategies, []
        )
        self._type_conflict_strategy_with_fail = TypeConflictFail(
            type_conflict_strategies
        )

    def type_conflict_strategy(self, *args):
        return self._type_conflict_strategy_with_fail(self, *args)


merger = CustomMerger(
    # pass in a list of tuple, with the strategies you are looking to apply
    # to each type.
    # NOTE(pas-ha) We are handling results of yaml.safe_load and k8s api
    # exclusively, thus only standard json-compatible collection data types
    # will be present, so not botherting with collections.abc for now.
    [(list, ["append"]), (dict, ["merge"])],
    # next, choose the fallback strategies, applied to all other types:
    ["override"],
    # finally, choose the strategies in the case where the types conflict:
    ["fail"],
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
        "barbican",
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


def services(spec, logger, **kwargs):
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
    """Merge releases and values from osdpl crd into service HelmBundle"""

    service_helmbundle = render_service_template(
        service, body, meta, spec, logger, **template_args
    )

    # FIXME(pas-ha) either move to dict merging stage before,
    # or move to the templates themselves
    service_helmbundle["spec"]["repositories"] = spec["common"]["charts"][
        "repositories"
    ]

    # We have 4 level of hierarchy, in increasing priority order:
    # 1. helm values.yaml - which is default
    # 2. osh_operator/templates/<openstack_version>/<helmbundle>.yaml
    # 3. OpenstackDeployment or profile charts section
    # 4. OpenstackDeployment or profile common/group section

    # The values are merged in this specific order.
    for release in service_helmbundle["spec"]["releases"]:
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
    return service_helmbundle


def merge_spec(spec, logger):
    """Merge user-defined OsDpl spec with base for profile and OS version"""
    os_release = spec["openstack_version"]
    profile = spec["profile"]
    logger.debug(f"Using profile {profile}")

    try:
        base = yaml.safe_load(
            ENV.get_template(f"{os_release}/{profile}.yaml").render()
        )
        # Merge operator defaults with user context.
        return merger.merge(base, spec)
    except Exception as e:
        raise kopf.HandlerFatalError(str(e))
