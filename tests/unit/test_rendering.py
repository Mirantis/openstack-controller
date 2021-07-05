import logging
import os
import yaml
from unittest import mock

from openstack_controller import constants
from openstack_controller import layers

logger = logging.getLogger(__name__)

OUTPUT_DIR = "tests/fixtures/render_service_template/output"
INPUT_DIR = "tests/fixtures/render_service_template/input"


def render_helmbundle(service, spec, **kwargs):
    data = layers.render_service_template(
        service,
        # osdpl body and metadata are not used in templates rendering
        {},
        {},
        spec,
        logging,
        **kwargs,
    )
    return data


def get_render_kwargs(service, context, default_args):
    service_t_args = {}
    with open(f"{INPUT_DIR}/{context}/context_template_args.yaml", "r") as f:
        context_template_args = yaml.safe_load(f)
        service_t_args = context_template_args[service]
        service_t_args["images"] = context_template_args.get(
            "images", default_args["images"]
        )
        service_t_args["admin_creds"] = context_template_args.get(
            "admin_creds", default_args["admin_creds"]
        )
        service_t_args["proxy_vars"] = context_template_args.get(
            "proxy_vars", default_args["proxy_vars"]
        )

    with open(f"{INPUT_DIR}/{context}/context_spec.yaml", "r") as f:
        spec = yaml.safe_load(f)

    return spec, service_t_args


@mock.patch.object(layers, "_get_dashboard_default_policy")
@mock.patch.object(layers, "_get_default_policy")
def test_render_service_template(
    gdp_mock, gddp_mock, common_template_args, dashboard_policy_default
):
    # Remove excluded services once contexts with these services are added
    excluded_services = {
        "tempest",
        "object-storage",
    }
    infra_services = {
        "messaging",
        "database",
        "memcached",
        "ingress",
        "redis",
        "coordination",
    }
    all_services = (
        set(constants.OS_SERVICES_MAP.keys())
        .union(infra_services)
        .difference(excluded_services)
    )
    for service in all_services:
        srv_dir = f"{OUTPUT_DIR}/{service}"
        contexts = [name.split(".")[0] for name in os.listdir(srv_dir)]
        if not contexts:
            raise RuntimeError(f"No contexts provided for service {service}")
        for context in contexts:
            if service == "dashboard":
                gdp_mock.return_value = {}
                gddp_mock.return_value = dashboard_policy_default
            elif service in infra_services:
                gdp_mock.return_value = {}
            else:
                gdp_mock.return_value = {
                    f"{service}_rule1": f"{service}_value1"
                }
            logger.debug(f"Rendering service {service} for context {context}")
            spec, kwargs = get_render_kwargs(
                service, context, common_template_args
            )
            data = render_helmbundle(service, spec, **kwargs)
            with open(f"{srv_dir}/{context}.yaml") as f:
                output = yaml.safe_load(f)
                assert data == output
