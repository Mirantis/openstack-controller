import copy
import functools

import deepmerge
import jinja2
import kopf
import pykube
import yaml

# TODO(pas-ha) enable debug logging

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


def login():
    try:
        # running in cluster
        config = pykube.KubeConfig.from_service_account()
    except FileNotFoundError:
        # not running in cluster => load local ~/.kube/config for testing
        config = pykube.KubeConfig.from_file()
    return pykube.HTTPClient(config)


api = login()
OpenStackDeployment = pykube.object_factory(
    api, "lcm.mirantis.com/v1alpha1", "OpenStackDeployment"
)


def make_kube_class(data):
    return pykube.object_factory(api, data["apiVersion"], data["kind"])


async def delete_service(service, *, body, meta, spec, logger, **kwargs):
    logger.info(f"Deleting config for {service}")
    logger.debug(f"found templates {ENV.list_templates()}")
    os_release = spec["common"]["openstack"]["version"]
    tpl = ENV.get_template(f"{os_release}/{service}.yaml")
    logger.info(f"using template {tpl.filename}")

    base = yaml.safe_load(ENV.get_template(f"{os_release}/base.yaml").render())
    # NOTE(pas-ha) not merging common and services as we only need correct name
    # (hardcoded in the template) and namespace (will be populated by adopt)
    # to delete the resource, base must be enough for that
    spec = merger.merge(base, spec)
    text = tpl.render(body=body, meta=meta, spec=spec)
    data = yaml.safe_load(text)
    kopf.adopt(data, body)
    # delete the object, already non-existing are auto-handled
    obj = make_kube_class(data)(api, data)
    obj.delete(propagation_policy="Foreground")
    logger.info(f"{obj.kind} {obj.namespace}/{obj.name} deleted")
    # remove child reference from status
    osdpl = (
        OpenStackDeployment.objects(api)
        .filter(namespace=meta["namespace"])
        .get(name=meta["name"])
    )
    status_patch = {"children": {obj.name: None}}
    osdpl.patch({"status": status_patch})
    kopf.info(
        body, reason="Delete", message=f"deleted {obj.kind} for {service}"
    )


async def apply_service(service, *, body, meta, spec, logger, event, **kwargs):
    logger.info(f"Applying config for {service}")
    logger.debug(f"found templates {ENV.list_templates()}")
    os_release = spec["common"]["openstack"]["version"]
    tpl = ENV.get_template(f"{os_release}/{service}.yaml")
    logger.info(f"Using template {tpl.filename}")

    base = yaml.safe_load(ENV.get_template(f"{os_release}/base.yaml").render())
    # Merge operator defaults with user context.
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
            spec.get("services", {})
            .get(service, {})
            .get(chart_name, {})
            .get("values", {}),
        )

    # NOTE(pas-ha) this sets the parent refs in child to point to our resource
    # so that cascading delete is handled by K8S itself
    kopf.adopt(data, body)
    # apply state of the object
    obj = make_kube_class(data)(api, data)
    if obj.exists():
        obj.reload()
        obj.set_obj(data)
        obj.update()
        logger.debug(f"{obj.kind} child is updated: %s", obj.obj)
    else:
        obj.create()
        logger.debug(f"{obj.kind} child is created: %s", obj.obj)
    # ensure child ref exists in the status
    osdpl = (
        OpenStackDeployment.objects(api)
        .filter(namespace=meta["namespace"])
        .get(name=meta["name"])
    )
    if obj.name not in osdpl.obj.get("status", {}).get("children", {}):
        status_patch = {"children": {obj.name: "Unknown"}}
        osdpl.patch({"status": status_patch})
    kopf.info(
        body,
        reason=event.capitalize(),
        message=f"{event}d {obj.kind} for {service}",
    )


async def update_status(owner, meta, status):
    osdpl = (
        OpenStackDeployment.objects(api)
        .filter(namespace=meta["namespace"])
        .get(name=owner)
    )
    child_status = {
        meta["name"]: all(
            s["success"] is True for n, s in status["releaseStatuses"].items()
        )
    }
    status_patch = {"children": child_status}
    new_children_status = copy.deepcopy(
        osdpl.obj["status"].get("children", {})
    )
    new_children_status.update(child_status)
    status_patch["deployed"] = all(
        s is True for c, s in new_children_status.items()
    )
    osdpl.patch({"status": status_patch})


@kopf.on.create("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def create(body, meta, spec, **kwargs):
    # TODO(pas-ha) remember children in CRD
    service_fns = {}
    for service in spec.get("features", {}).get("services", []):
        service_fns[service] = functools.partial(
            apply_service, service=service
        )
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "created"}
    else:
        return {"message": "skipped"}


@kopf.on.update("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def update(body, meta, spec, logger, **kwargs):
    # NOTE(pas-ha) each diff is (op, (path, parts, ...), old, new)
    # kopf ignores changes to status except its own internal fields
    # and metadata except labels and annotations
    # (kind and apiVersion and namespace are de-facto immutable)
    deleted_services = {}
    for op, path, old, new in kwargs["diff"]:
        logger.info(f"{op} {'.'.join(path)} from {old} to {new}")
        if path == ("spec", "features", "services"):
            # NOTE(pas-ha) something changed in services,
            # need to check if any were deleted
            deleted_services = set(old) - set(new)
            if deleted_services:
                logger.info(f"deleted services {' '.join(deleted_services)}")
    service_fns = {}
    for service in spec.get("features", {}).get("services", []):
        service_fns[service] = functools.partial(
            apply_service, service=service
        )
    for service in deleted_services:
        service_fns[service + "_delete"] = functools.partial(
            delete_service, service=service
        )
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "updated"}
    else:
        return {"message": "skipped"}


@kopf.on.delete("lcm.mirantis.com", "v1alpha1", "openstackdeployments")
async def delete(meta, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    logger.info(f"deleting {meta['name']}")


@kopf.on.field("lcm.mirantis.com", "v1alpha1", "helmbundles", field="status")
async def status(body, meta, status, logger, diff, **kwargs):
    namespace = meta["namespace"]
    owners = [
        o["name"]
        for o in meta["ownerReferences"]
        if o["kind"] == OpenStackDeployment.kind
        and o["apiVersion"] == OpenStackDeployment.version
    ]
    if not owners:
        logger.info("not managed by osh-operator, ignoring")
        return
    elif len(owners) > 1:
        logger.error(
            f"several owners of kind OpenStackDeployment "
            f"for {body['kind']} {namespace}/{meta['name']}!"
        )
        raise NotImplementedError
    await update_status(owners[0], meta, status)
    logger.info(f"Updated {meta['name']} status in {owners[0]}")
