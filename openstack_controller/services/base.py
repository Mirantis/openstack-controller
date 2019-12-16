import asyncio
import base64
import json
import logging
import os
import socket
from typing import List

import kopf
from mcp_k8s_lib import ceph_api
import pykube

from openstack_controller import layers
from openstack_controller import kube
from openstack_controller import openstack
from openstack_controller import secrets
from openstack_controller import version


LOG = logging.getLogger(__name__)


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


class GenericChildObject:
    def __init__(self, service, chart):
        self.chart = chart
        self.service = service
        self.namespace = service.namespace

    def _get_job_object(self, suffix, manifest, images):
        child_obj = kube.dummy(
            kube.Job, f"{self.chart}-{suffix}", self.namespace
        )
        helmbundle_ext = kube.HelmBundleExt(self.chart, manifest, images)
        child_obj.helmbundle_ext = helmbundle_ext
        child_obj.service = self.service

        return child_obj

    def job_db_init(self):
        return self._get_job_object("db-init", "job_db_init", ["db_init"])

    def job_db_sync(self):
        return self._get_job_object(
            "db-sync", "job_db_sync", [f"{self.chart}_db_sync"]
        )

    def job_db_drop(self):
        return self._get_job_object("db-drop", "job_db_drop", ["db_drop"])

    def job_ks_endpoints(self):
        return self._get_job_object(
            "ks-endpoints", "job_ks_endpoints", ["ks_endpoints"]
        )

    def job_ks_service(self):
        return self._get_job_object(
            "ks-service", "job_ks_service", ["ks_service"]
        )

    def job_ks_user(self):
        return self._get_job_object("ks-user", "job_ks_user", ["ks_user"])

    def job_bootstrap(self):
        return self._get_job_object(
            "bootstrap", "job_bootstrap", ["bootstrap"]
        )


class Service(RuntimeIdentifierMixin):

    ceph_required = False
    service = None
    group = "lcm.mirantis.com"
    version = "v1alpha1"
    kind = "HelmBundle"
    registry = {}
    _child_objects = {
        #       '<chart>': {
        #           '<Kind>': {
        #               '<kubernetes resource name>': {
        #                   'images': ['List of images'],
        #                   'manifest': '<manifest flag>'
        #               }
        #           }
        #       }
    }

    _service_accounts = []
    _required_accounts = {}

    @property
    def service_accounts(self) -> List[str]:
        service_name = openstack.OS_SERVICES_MAP.get(self.service)
        if service_name:
            return self._service_accounts + [service_name, "test"]
        return self._service_accounts

    @property
    def _child_generic_objects(self):
        return {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        cls.registry[cls.service] = cls

    def __init__(self, body, logger):
        self.osdpl = kube.OpenStackDeployment(kube.api, body)
        self.namespace = self.osdpl.namespace
        self.logger = logger

    @property
    def resource_name(self):
        return f"openstack-{self.service}"

    @property
    def resource_def(self):
        """Minimal representation of the resource"""
        fingerprint = layers.spec_hash(self.osdpl.obj)
        annotations = {
            f"{self.group}/openstack-controller-fingerprint": json.dumps(
                {
                    "osdpl_generation": self.osdpl.metadata["generation"],
                    "version": version.release_string,
                    "fingerprint": fingerprint,
                }
            )
        }
        res = {
            "apiVersion": f"{self.group}/{self.version}",
            "kind": self.kind,
            "metadata": {
                "name": self.resource_name,
                "annotations": annotations,
            },
        }
        return res

    def _get_generic_child_objects(self):
        res = []
        for chart, items in self._child_generic_objects.items():
            for item in items:
                res.append(
                    GenericChildObject(self, chart).__getattribute__(item)()
                )
        return res

    @property
    def child_objects(self):
        res = []

        for chart_name, charts in self._child_objects.items():
            child = {}
            m_ext = {}
            for kind, kinds in charts.items():
                child["kind"] = kind
                for kind_name, meta in kinds.items():
                    m_ext = meta
                    m_ext["chart"] = chart_name
                    m_ext_obj = kube.HelmBundleExt(**m_ext)

                    child_obj = kube.dummy(
                        kube.__getattribute__(kind), kind_name, self.namespace
                    )
                    child_obj.helmbundle_ext = m_ext_obj
                    child_obj.service = self
                    res.append(child_obj)
        return res + self._get_generic_child_objects()

    def set_release_values(self, values):
        data = self.resource_def
        kopf.adopt(data, self.osdpl.obj)
        obj = kube.resource(data)
        obj.reload()
        data = obj.obj

        for release in data["spec"]["releases"]:
            layers.merger.merge(release["values"], values)
        obj.update()
        self.logger.info(f"Update {self.service} with {values}")

    def get_child_object(self, kind, name):
        return [
            child
            for child in self.child_objects
            if child.kind == kind and child.name == name
        ][0]

    def update_status(self, patch):
        self.osdpl.patch({"status": patch})

    async def cleanup_immutable_resources(self):
        old_data = self.resource_def
        kopf.adopt(old_data, self.osdpl.obj)
        old_obj = kube.resource(old_data)
        old_obj.reload()

        new_data = self.render()
        kopf.adopt(new_data, self.osdpl.obj)
        new_obj = kube.resource(new_data)

        to_cleanup = []

        def _is_image_changed(image, chart):
            for old_release in old_obj.obj["spec"]["releases"]:
                if old_release["chart"].endswith(f"/{chart}"):
                    for new_release in new_obj.obj["spec"]["releases"]:
                        if new_release["chart"].endswith(f"/{chart}"):
                            old_image = old_release["values"]["images"][
                                "tags"
                            ].get(image)
                            new_image = new_release["values"]["images"][
                                "tags"
                            ][image]
                            # When image name is changed it will not present in helmbundle object
                            # on deployed environmet. At the same time in current version of code
                            # we will use new name of image.
                            if old_image is None:
                                return True
                            if old_image != new_image:
                                return True

        for resource in self.child_objects:
            if resource.immutable:
                for image in resource.helmbundle_ext.images:
                    if _is_image_changed(image, resource.helmbundle_ext.chart):
                        to_cleanup.append(resource)
                        # Break on first image match.
                        break

        self.logger.info(f"Removing the following jobs: {to_cleanup}")
        tasks = set()
        for child_object in to_cleanup:
            tasks.add(child_object.purge())

        await asyncio.gather(*tasks)

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
        # ensure child ref exists in the status
        if self.resource_name not in self.osdpl.obj.get("status", {}).get(
            "children", {}
        ):
            status_patch = {"children": {self.resource_name: "Unknown"}}
            self.update_status(status_patch)
        if self.ceph_required:
            self.ensure_ceph_secrets()
        self.logger.info(f"Applying config for {self.service}")
        data = self.render()
        kopf.adopt(data, self.osdpl.obj)
        obj = kube.resource(data)
        # apply state of the object
        if obj.exists():
            # Drop immutable resources (jobs) before changing theirs values.
            await self.cleanup_immutable_resources()
            # TODO(pas-ha) delete jobs if image was changed
            obj.reload()
            obj.set_obj(data)
            obj.update()
            self.logger.debug(f"{obj.kind} child is updated: %s", obj.obj)
        else:
            obj.create()
            self.logger.debug(f"{obj.kind} child is created: %s", obj.obj)
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
        service_creds = secrets.get_or_create_service_credentials(
            self.namespace,
            self.service,
            self.service_accounts,
            self._required_accounts,
        )

        template_args = {
            "credentials": credentials,
            "admin_creds": admin_creds,
            "service_creds": service_creds,
        }
        if self.ceph_required:
            template_args.update(self.ceph_config())

        return template_args

    @layers.kopf_exception
    def render(self, openstack_version=""):
        spec = layers.merge_spec(self.osdpl.obj["spec"], self.logger)
        if openstack_version:
            spec["openstack_version"] = openstack_version
        template_args = self.template_args(spec)
        data = layers.merge_all_layers(
            self.service,
            self.osdpl.obj,
            self.osdpl.metadata,
            spec,
            self.logger,
            **template_args,
        )
        data.update(self.resource_def)
        # NOTE(pas-ha) this sets the parent refs in child
        # to point to our resource so that cascading delete
        # is handled by K8s itself
        kopf.adopt(data, self.osdpl.obj)
        return data

    def get_image(self, name, chart, openstack_version=None):
        data = self.render(openstack_version)
        for release in data["spec"]["releases"]:
            if release["chart"].endswith(f"/{chart}"):
                return release["values"]["images"]["tags"][name]


class OpenStackService(Service):
    openstack_chart = None

    @property
    def _child_generic_objects(self):
        return {
            f"{self.openstack_chart}": {
                "job_db_init",
                "job_db_sync",
                "job_db_drop",
                "job_ks_endpoints",
                "job_ks_service",
                "job_ks_user",
                "job_bootstrap",
            }
        }
