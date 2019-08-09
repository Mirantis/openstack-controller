import functools

import base64
from distutils.util import strtobool
import kopf
import pykube
import re
from ipaddress import IPv4Address


from mcp_k8s_lib import ceph_api
from . import kube
from . import layers


# TODO(pas-ha) enable debug logging


async def delete_service(service, *, body, meta, spec, logger, **kwargs):
    logger.info(f"Deleting config for {service}")
    data = layers.render_all(service, body, meta, spec, logger)
    kopf.adopt(data, body)

    # delete the object, already non-existing are auto-handled
    obj = kube.resource(data)
    obj.delete(propagation_policy="Foreground")
    logger.info(f"{obj.kind} {obj.namespace}/{obj.name} deleted")
    # remove child reference from status
    osdpl = kube.find_osdpl(meta["name"], namespace=meta["namespace"])
    status_patch = {"children": {obj.name: None}}
    osdpl.patch({"status": status_patch})
    kopf.info(
        body, reason="Delete", message=f"deleted {obj.kind} for {service}"
    )


def wait_for_rook_secret(namespace, name):
    kube.wait_for_resource(pykube.Secret, name, namespace)


def get_rook_ceph_data(namespace=ceph_api.SHARED_SECRET_NAMESPACE):
    # TODO: switch to kaas ceph operator data
    secret = kube.find(pykube.Secret, "rook-ceph-admin-keyring", namespace)
    keyring = base64.b64decode(secret.obj["data"]["keyring"]).decode()
    m = re.search("key = ((\S)+)", keyring)
    key = m.group(1)
    endpoints_obj = kube.find(
        pykube.ConfigMap, "rook-ceph-mon-endpoints", namespace
    ).obj
    endp_mapping = endpoints_obj["data"]["data"]
    endpoints = [x.split("=")[1] for x in endp_mapping.split(",")]
    mon_endpoints = []
    rgw_params = ceph_api.RGWParams(internal_url="", external_url="")
    for endpoint in endpoints:
        address = endpoint.split(":")[0]
        port = endpoint.split(":")[1]
        mon_endpoints.append((IPv4Address(address), port))
    oscp = ceph_api.OSCephParams(
        admin_key=key, mon_endpoints=mon_endpoints, services=[], rgw=rgw_params
    )
    return oscp


# def get_rook_ceph_data(namespace, name):
#    secret = kube.find(pykube.Secret, name, namespace)
#    return json.loads(base64.b64decode(secret.obj['data']['key']))


# def get_rook_ceph_params():
#    os_ceph_params = ceph.get_os_ceph_params(get_rook_ceph_data)


def check_ceph_required(service, meta):
    return strtobool(
        meta.get("annotations", {}).get(
            "lcm.mirantis.com/ceph_required", "False"
        )
    )


def check_ceph_resources_present(osdpl):
    status = []
    for resource in ["configmap", "secret"]:
        status.append(
            osdpl.obj.get("status", {}).get("ceph", {}).get(resource)
            == "created"
        )
    return all(status)


def save_ceph_secret(name, namespace, params: ceph_api.OSCephParams):
    key_data = f"""
[{params.admin_user}]
         key = {params.admin_key}
    """
    secret = {
        "metadata": {"name": name, "namespace": namespace},
        "data": {"key": base64.b64encode(key_data.encode()).decode()},
    }
    try:
        pykube.Secret(kube.api, secret).create()
    except Exception:
        # TODO check for resource exists exception.
        pass


def save_ceph_configmap(name, namespace, params: ceph_api.OSCephParams):
    mon_host = ",".join([f"{ip}:{port}" for ip, port in params.mon_endpoints])
    ceph_conf = f"""
[global]
         mon host = {mon_host}

    """
    configmap = {
        "metadata": {"name": name, "namespace": namespace},
        "data": {"ceph.conf": ceph_conf},
    }
    try:
        pykube.ConfigMap(kube.api, configmap).create()
    except Exception:
        # TODO check for resource exists exception.
        pass


async def apply_service(service, *, body, meta, spec, logger, event, **kwargs):
    logger.info(f"Applying config for {service}")
    data = layers.render_all(service, body, meta, spec, logger)

    # NOTE(pas-ha) this sets the parent refs in child to point to our resource
    # so that cascading delete is handled by K8s itself
    kopf.adopt(data, body)
    # apply state of the object
    obj = kube.resource(data)
    namespace = meta["namespace"]
    osdpl = kube.find_osdpl(meta["name"], namespace=namespace)
    if check_ceph_required(
        service, data["metadata"]
    ) and not check_ceph_resources_present(osdpl):
        try:
            kube.find(
                pykube.Secret, ceph_api.CEPH_OPENSTACK_TARGET_SECRET, namespace
            )
            kube.find(
                pykube.ConfigMap,
                ceph_api.CEPH_OPENSTACK_TARGET_CONFIGMAP,
                namespace,
            )
            logger.info("Secret and Configmap are present.")
        except:
            logger.info("Waiting for ceph resources.")
            status_patch = {
                "ceph": {
                    "secret": ceph_api.CephStatus.waiting,
                    "configmap": ceph_api.CephStatus.waiting,
                }
            }
            osdpl.patch({"status": status_patch})
            wait_for_rook_secret(
                ceph_api.SHARED_SECRET_NAMESPACE, "rook-ceph-admin-keyring"
            )
            oscp = get_rook_ceph_data()
            save_ceph_secret(
                ceph_api.CEPH_OPENSTACK_TARGET_SECRET, namespace, oscp
            )
            save_ceph_configmap(
                ceph_api.CEPH_OPENSTACK_TARGET_CONFIGMAP, namespace, oscp
            )
            status_patch = {
                "ceph": {
                    "secret": ceph_api.CephStatus.created,
                    "configmap": ceph_api.CephStatus.created,
                }
            }
            osdpl.patch({"status": status_patch})
            logger.info("Ceph resources were created successfully.")

    if obj.exists():
        obj.reload()
        obj.set_obj(data)
        obj.update()
        logger.debug(f"{obj.kind} child is updated: %s", obj.obj)
    else:
        obj.create()
        logger.debug(f"{obj.kind} child is created: %s", obj.obj)
    # ensure child ref exists in the status
    if obj.name not in osdpl.obj.get("status", {}).get("children", {}):
        status_patch = {"children": {obj.name: "Unknown"}}
        osdpl.patch({"status": status_patch})
    kopf.info(
        body,
        reason=event.capitalize(),
        message=f"{event}d {obj.kind} for {service}",
    )


@kopf.on.create(*kube.OpenStackDeployment.kopf_on_args)
async def create(body, meta, spec, logger, **kwargs):
    create, delete = layers.services(spec, logger, **kwargs)
    service_fns = {
        s: functools.partial(apply_service, service=s) for s in create
    }
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "created"}
    else:
        return {"message": "skipped"}


@kopf.on.update(*kube.OpenStackDeployment.kopf_on_args)
async def update(body, meta, spec, logger, **kwargs):
    update, delete = layers.services(spec, logger, **kwargs)
    if delete:
        logger.info(f"deleting children {' '.join(delete)}")
    service_fns = {
        s: functools.partial(apply_service, service=s) for s in update
    }
    for service in delete:
        service_fns[service + "_delete"] = functools.partial(
            delete_service, service=service
        )
    if service_fns:
        await kopf.execute(fns=service_fns)
        return {"message": "updated"}
    else:
        return {"message": "skipped"}


@kopf.on.delete(*kube.OpenStackDeployment.kopf_on_args)
async def delete(meta, logger, **kwargs):
    # TODO(pas-ha) wait for children to be deleted
    logger.info(f"deleting {meta['name']}")
