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
    ],
    "infra": ["rabbitmq", "mariadb", "memcached", "openvswitch", "libvirt"],
}


def apply_helmbundle_state(data):
    api = kubernetes.client.CustomObjectsApi()
    name = data["metadata"]["name"]
    namespace = data["metadata"].get("namespace", "default")

    args = dict(
        group="lcm.mirantis.com",
        version="v1alpha1",
        plural="helmbundles",
        namespace=namespace,
    )
    current = None
    try:
        current = api.get_namespaced_custom_object(name=name, **args)
    except Exception:  # FIXME(pas-ha) use more narrow exception for 404
        pass

    if current:
        data["metadata"]["resourceVersion"] = current["metadata"][
            "resourceVersion"
        ]
        hb = api.replace_namespaced_custom_object(name=name, body=data, **args)
    else:
        hb = api.create_namespaced_custom_object(body=data, **args)
    return hb


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
            spec["services"]
            .get(service, {})
            .get(chart_name, {})
            .get("values", {}),
        )

    # NOTE(pas-ha) this sets the parent refs in child to point to our resource
    # so that cascading delete is handled by K8S itself
    kopf.adopt(data, body)
    logger.info(f"Creating HelmBundle object: %s", data)
    obj = apply_helmbundle_state(data)
    # TODO(pas-ha) poll/retry for children to be created/updated
    logger.info(f"HelmBundle child is created: %s", obj)


@kopf.on.create("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def create(body, meta, spec, logger, **kwargs):
    # TODO(pas-ha) remember children in CRD
    service_fns = {}
    for service in spec.get("features", {}).get("services", []):
        service_fns[service] = functools.partial(
            handle_service, service=service
        )
    await kopf.execute(fns=service_fns)
    return {"message": "created!"}


@kopf.on.update("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def update(body, meta, spec, logger, **kwargs):
    # TODO(pas-ha) handle deleted services
    logger.debug(f"event is {kwargs['event']}")
    logger.debug(f"status is {kwargs['status']}")
    logger.debug(f"patch is {kwargs['patch']}")

    # NOTE(pas-ha) each diff is (op, (path, parts), old, new)
    # we react only on metadata and spec changes,
    # anything else should be out of control of API user
    accept_update = ("metadata", "spec")
    needs_update = False
    for op, path, old, new in kwargs["diff"]:
        if path[0] in accept_update:
            logger.info(f"{op} {'.'.join(path)} from {old} to {new}")
            needs_update = True
    if not needs_update:
        logger.info(
            f"no {' or '.join(accept_update)} changes for {meta['name']}, "
            f"ignoring update"
        )
        return

    service_fns = {}
    for service in spec.get("features", {}).get("services", []):
        service_fns[service] = functools.partial(
            handle_service, service=service
        )
    await kopf.execute(fns=service_fns)
    kopf.info(body, reason="Update", message=f"updated {meta['name']}")
    return {"message": "success"}


@kopf.on.delete("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def delete(meta, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    logger.info(f"deleting {meta['name']}")
