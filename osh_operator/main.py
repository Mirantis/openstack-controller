import functools

import deepmerge
import jinja2
import kopf
import kubernetes
import yaml


ENV = jinja2.Environment(loader=jinja2.PackageLoader("osh_operator"))

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
    ],
    "infra": ["rabbitmq", "mariadb", "memcached", "openvswitch", "libvirt"],
}


def handle_service(service, *, body, meta, spec, logger, **kwargs):
    logger.info(f"found templates {ENV.list_templates()}")
    os_release = spec["common"]["openstack"]["version"]
    tpl = ENV.get_template(f"{os_release}/{service}.yaml")
    logger.info(f"template file is {tpl.filename}")

    # Merge operator defaults with user context.
    base_file = ENV.get_template(f"{os_release}/base.yaml").filename
    with open(base_file) as f:
        base = yaml.safe_load(f)
    spec = merger.merge(base, spec)
    text = tpl.render(body=body, meta=meta, spec=spec)
    data = yaml.safe_load(text)

    # FIXME(pas-ha) either move to dict merging stage before,
    # or move to the templates themselves
    data["spec"]["repositories"] = spec["common"]["charts"]["repositories"]

    # We have 4 level of hierarhy:
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
            spec["services"].get(chart_name, {}).get("values", {}),
        )

    kopf.adopt(data, body)
    logger.info(f"Creating HelmBundle object: %s", data)
    api = kubernetes.client.CustomObjectsApi()
    obj = api.create_namespaced_custom_object(
        "lcm.mirantis.com",
        "v1alpha1",
        meta.get("namespace", "default"),
        "helmbundles",
        body=data,
    )
    logger.info(f"HelmBundle child is created: %s", obj)


@kopf.on.create("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def create(body, meta, spec, logger, **kwargs):
    service_fns = {}
    for service in spec.get("services", {}).keys():
        service_fns[service] = functools.partial(
            handle_service, service=service
        )
    await kopf.execute(fns=service_fns)
    return {"message": "created!"}


@kopf.on.update("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def update(body, spec, logger, diff, patch, **kwargs):
    logger.info(f"Update DIFF is {diff}")
    logger.info(f"Update PATCH is {patch}")
    return {"message": "updated {meta['name']} with {diff}"}


@kopf.on.delete("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def delete(meta, logger, **kwargs):
    logger.info(f"deleting {meta['name']}")
    return {"message": "by world"}
