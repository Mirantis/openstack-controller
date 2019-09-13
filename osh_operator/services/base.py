import base64
from ipaddress import IPv4Address
import re

import kopf
from mcp_k8s_lib import ceph_api
import pykube

from osh_operator import layers
from osh_operator import kube
from osh_operator import openstack


class Service:

    ceph_required = False
    service = None
    registry = {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        cls.registry[cls.service] = cls

    def __init__(self, body, logger):
        self.osdpl = kube.OpenStackDeployment(kube.api, body)
        self.namespace = self.osdpl.namespace
        self.logger = logger

    def set_parent_status(self, patch):
        self.osdpl.patch({"status": patch})

    async def delete(self, *, body, meta, spec, logger, **kwargs):
        self.logger.info(f"Deleting config for {self.service}")
        # TODO(e0ne): remove credentials of the deleted services
        data = self.render()
        # delete the object, already non-existing are auto-handled
        obj = kube.resource(data)
        obj.delete(propagation_policy="Foreground")
        self.logger.info(f"{obj.kind} {obj.namespace}/{obj.name} deleted")
        # remove child reference from status
        self.set_parent_status({"children": {obj.name: None}})
        kopf.info(
            body,
            reason="Delete",
            message=f"deleted {obj.kind} for {self.service}",
        )

    async def apply(self, event, **kwargs):
        if self.ceph_required:
            self.ensure_ceph_secrets()
        self.logger.info(f"Applying config for {self.service}")
        data = self.render()
        kopf.adopt(data, self.osdpl.obj)
        obj = kube.resource(data)
        # apply state of the object
        if obj.exists():
            # TODO(pas-ha) delete jobs if image was changed
            obj.reload()
            obj.set_obj(data)
            obj.update()
            self.logger.debug(f"{obj.kind} child is updated: %s", obj.obj)
        else:
            obj.create()
            self.logger.debug(f"{obj.kind} child is created: %s", obj.obj)
        # ensure child ref exists in the status
        if obj.name not in self.osdpl.obj.get("status", {}).get(
            "children", {}
        ):
            status_patch = {"children": {obj.name: "Unknown"}}
            self.set_parent_status(status_patch)
        kopf.info(
            self.osdpl.obj,
            reason=event.capitalize(),
            message=f"{event}d {obj.kind} for {self.service}",
        )

    def ensure_ceph_secrets(self):
        self.osdpl.reload()
        if all(
            self.osdpl.obj.get("status", {}).get("ceph", {}).get(res)
            == "created"
            for res in ("configmap", "secret")
        ):
            return
        if not (
            kube.dummy(
                pykube.Secret,
                ceph_api.CEPH_OPENSTACK_TARGET_SECRET,
                self.osdpl.namespace,
            ).exists()
            and kube.dummy(
                pykube.ConfigMap,
                ceph_api.CEPH_OPENSTACK_TARGET_CONFIGMAP,
                self.osdpl.namespace,
            ).exists()
        ):
            self.create_ceph_secrets()
        else:
            self.logger.info("Secret and Configmap are present.")

    def create_ceph_secrets(self):
        self.logger.info("Waiting for ceph resources.")
        # FIXME(pas-ha) race? we can re-write result of parallel thread..
        # but who cares TBH
        self.set_parent_status(
            {
                "ceph": {
                    "secret": ceph_api.CephStatus.waiting,
                    "configmap": ceph_api.CephStatus.waiting,
                }
            }
        )
        kube.wait_for_secret(
            ceph_api.SHARED_SECRET_NAMESPACE, "rook-ceph-admin-keyring"
        )
        oscp = self.get_rook_ceph_data()
        self.save_ceph_secret(oscp)
        self.save_ceph_configmap(oscp)
        self.set_parent_status(
            {
                "ceph": {
                    "secret": ceph_api.CephStatus.created,
                    "configmap": ceph_api.CephStatus.created,
                }
            }
        )
        self.logger.info("Ceph resources were created successfully.")

    def get_rook_ceph_data(self, namespace=ceph_api.SHARED_SECRET_NAMESPACE):
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
            admin_key=key,
            mon_endpoints=mon_endpoints,
            services=[],
            rgw=rgw_params,
        )
        return oscp

    def save_ceph_secret(self, params: ceph_api.OSCephParams):
        key_data = f"[{params.admin_user}]\n        key = {params.admin_key}\n"
        secret = {
            "metadata": {
                "name": ceph_api.CEPH_OPENSTACK_TARGET_SECRET,
                "namespace": self.osdpl.namespace,
            },
            "data": {"key": base64.b64encode(key_data.encode()).decode()},
        }
        try:
            pykube.Secret(kube.api, secret).create()
        except Exception:
            # TODO check for resource exists exception.
            pass

    def save_ceph_configmap(self, params: ceph_api.OSCephParams):
        mon_host = ",".join(
            [f"{ip}:{port}" for ip, port in params.mon_endpoints]
        )
        ceph_conf = f"[global]\n        mon host = {mon_host}\n"
        configmap = {
            "metadata": {
                "name": ceph_api.CEPH_OPENSTACK_TARGET_CONFIGMAP,
                "namespace": self.osdpl.namespace,
            },
            "data": {"ceph.conf": ceph_conf},
        }
        try:
            pykube.ConfigMap(kube.api, configmap).create()
        except Exception:
            # TODO check for resource exists exception.
            pass

    def template_args(self, spec):
        credentials = openstack.get_or_create_os_credentials(
            self.service, self.namespace
        )
        admin_creds = openstack.get_admin_credentials(self.namespace)
        return {"credentials": credentials, "admin_creds": admin_creds}

    def render(self):
        spec = layers.merge_spec(self.osdpl.obj["spec"], self.logger)
        try:
            template_args = self.template_args(spec)
            data = layers.merge_all_layers(
                self.service,
                self.osdpl.obj,
                self.osdpl.metadata,
                spec,
                self.logger,
                **template_args,
            )
        except Exception as e:
            raise kopf.HandlerFatalError(str(e))
        # NOTE(pas-ha) this sets the parent refs in child
        # to point to our resource so that cascading delete
        # is handled by K8s itself
        kopf.adopt(data, self.osdpl.obj)
        return data
