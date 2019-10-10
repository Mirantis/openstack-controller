import base64
import os, socket

import kopf
from mcp_k8s_lib import ceph_api
import pykube

from osh_operator import layers
from osh_operator import kube
from osh_operator import openstack
from osh_operator import secrets


class RuntimeIdentifierMixin:
    @property
    def runtime_identifier(self):
        pgrp = os.getpgrp()
        hostname = socket.gethostname()
        return f"{hostname}_{pgrp}"

    @property
    def latest_runtime_identifier(self):
        return (
            self.osdpl.obj.get("status", {})
            .get("runtime_identitfier", {})
            .get(self.service)
        )

    def set_runtime_identifier(self):
        self.logger.info(
            f"Setting runtime identifier to osdpl service {self.service}."
        )
        patch = {
            "runtime_identitfier": {self.service: self.runtime_identifier}
        }
        self.update_status(patch)

    @property
    def is_identifier_changed(self):
        return self.runtime_identifier != self.latest_runtime_identifier


class Service(RuntimeIdentifierMixin):

    ceph_required = False
    service = None
    version = "lcm.mirantis.com/v1alpha1"
    kind = "HelmBundle"
    registry = {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        cls.registry[cls.service] = cls

    def __init__(self, body, logger):
        self.osdpl = kube.OpenStackDeployment(kube.api, body)
        self.namespace = self.osdpl.namespace
        self.logger = logger

    @property
    def resource_def(self):
        """Minimal representation of the resource"""
        res = {
            "apiVersion": self.version,
            "kind": self.kind,
            "metadata": {"name": f"openstack-{self.service}"},
        }
        return res

    def update_status(self, patch):
        self.osdpl.patch({"status": patch})

    async def delete(self, *, body, meta, spec, logger, **kwargs):
        self.logger.info(f"Deleting config for {self.service}")
        # TODO(e0ne): remove credentials of the deleted services
        data = self.resource_def
        kopf.adopt(data, self.osdpl.obj)
        obj = kube.resource(data)
        # delete the object, already non-existing are auto-handled
        obj.delete(propagation_policy="Foreground")
        self.logger.info(f"{obj.kind} {obj.namespace}/{obj.name} deleted")
        # remove child reference from status
        self.update_status({"children": {obj.name: None}})
        kopf.info(
            body,
            reason="Delete",
            message=f"deleted {obj.kind} for {self.service}",
        )

    async def apply(self, event, **kwargs):
        self.set_runtime_identifier()
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
            self.update_status(status_patch)
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
                self.namespace,
            ).exists()
            and kube.dummy(
                pykube.ConfigMap,
                ceph_api.CEPH_OPENSTACK_TARGET_CONFIGMAP,
                self.namespace,
            ).exists()
        ):
            self.create_ceph_secrets()
        else:
            self.logger.info("Secret and Configmap are present.")

    def create_ceph_secrets(self):
        self.logger.info("Waiting for ceph resources.")
        # FIXME(pas-ha) race? we can re-write result of parallel thread..
        # but who cares TBH
        self.update_status(
            {
                "ceph": {
                    "secret": ceph_api.CephStatus.waiting,
                    "configmap": ceph_api.CephStatus.waiting,
                }
            }
        )
        kube.wait_for_secret(
            ceph_api.SHARED_SECRET_NAMESPACE, ceph_api.OPENSTACK_KEYS_SECRET
        )
        oscp = ceph_api.get_os_ceph_params(secrets.get_secret_data)
        # TODO(vsaienko): the subset of secrets might be changed after
        # deployment. For example additional service is deployed,
        # we need to handle this.
        self.save_ceph_secrets(oscp)
        self.save_ceph_configmap(oscp)
        self.update_status(
            {
                "ceph": {
                    "secret": ceph_api.CephStatus.created,
                    "configmap": ceph_api.CephStatus.created,
                }
            }
        )
        self.logger.info("Ceph resources were created successfully.")

    def save_ceph_secrets(self, params: ceph_api.OSCephParams):
        for service in params.services:
            name = ceph_api.get_os_user_keyring_name(service.user)
            secret = {
                "metadata": {"name": name, "namespace": self.namespace},
                "data": {
                    "key": base64.b64encode(service.key.encode()).decode()
                },
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
                "namespace": self.namespace,
            },
            "data": {"ceph.conf": ceph_conf},
        }
        try:
            pykube.ConfigMap(kube.api, configmap).create()
        except Exception:
            # TODO check for resource exists exception.
            pass

    @staticmethod
    def get_ceph_role_pools(oscp: ceph_api.OSServiceCreds):
        ret = {}
        service_user = oscp.user.name
        for pool in oscp.pools:
            if pool.role.name in ceph_api.CEPH_POOL_ROLE_SERVICES_MAP.get(
                service_user
            ):
                ret.update(
                    {pool.name: {"name": pool.name, "role": pool.role.name}}
                )

        return ret

    def ceph_config(self):
        ceph_config = {}
        oscp = ceph_api.get_os_ceph_params(secrets.get_secret_data)
        for oscp_service in oscp.services:
            srv_username = openstack.OS_SERVICES_MAP.get(self.service)
            if oscp_service.user.name == srv_username:
                ceph_config[srv_username] = {
                    "username": srv_username,
                    "keyring": oscp_service.key,
                    "secrets": ceph_api.get_os_user_keyring_name(
                        oscp_service.user
                    ),
                    "pools": self.get_ceph_role_pools(oscp_service),
                }
        return {"ceph": ceph_config}

    def template_args(self, spec):
        credentials = openstack.get_or_create_os_credentials(
            self.service, self.namespace
        )
        admin_creds = openstack.get_admin_credentials(self.namespace)
        template_args = {
            "credentials": credentials,
            "admin_creds": admin_creds,
        }
        if self.ceph_required:
            template_args.update(self.ceph_config())

        return template_args

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
        data.update(self.resource_def)
        kopf.adopt(data, self.osdpl.obj)
        return data
