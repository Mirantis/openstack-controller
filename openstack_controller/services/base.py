import asyncio
import base64
import json
from jsonpath_ng import parse
from typing import List
import hashlib

import kopf
import pykube

from openstack_controller import ceph_api
from openstack_controller import constants
from openstack_controller import health
from openstack_controller import layers
from openstack_controller import kube
from openstack_controller import secrets
from openstack_controller import settings
from openstack_controller import version
from openstack_controller import utils


LOG = utils.get_logger(__name__)


class GenericChildObject:
    def __init__(self, service, chart):
        self.chart = chart
        self.service = service
        self.namespace = service.namespace

    def _get_job_object(self, suffix, manifest, images, hash_fields=None):
        child_obj = kube.dummy(
            kube.Job, f"{self.chart}-{suffix}", self.namespace
        )
        if hash_fields is None:
            hash_fields = []
        helmbundle_ext = kube.HelmBundleExt(
            self.chart, manifest, images, hash_fields=hash_fields
        )
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


class Service:

    service = None
    namespace = None
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
    _secret_class = secrets.OpenStackServiceSecret

    @property
    def service_accounts(self) -> List[str]:
        service_name = constants.OS_SERVICES_MAP.get(self.service)
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
        # TODO(e0ne): we need to omit this object usage in the future to
        # not face side-effects with mutable PyKube OSDPL object.
        # We have to use self._get_osdpl() method instead of it.
        self.osdpl = kube.OpenStackDeployment(kube.api, body)
        self.body = body
        if self.namespace is None:
            self.namespace = body["metadata"]["namespace"]
        self.logger = logger
        self.openstack_version = self.body["spec"]["openstack_version"]
        self.mspec = layers.merge_spec(self.body["spec"], self.logger)

    def _get_helmbundle(self):
        data = self.resource_def
        kopf.adopt(data, self.osdpl.obj)
        return kube.resource(data)

    def _get_osdpl(self):
        osdpl = kube.OpenStackDeployment(kube.api, self.body)
        osdpl.reload()
        return osdpl

    def _get_admin_creds(self) -> secrets.OpenStackAdminCredentials:
        admin_secret = secrets.OpenStackAdminSecret(self.namespace)
        return admin_secret.ensure()

    @property
    def resource_name(self):
        return f"openstack-{self.service}"

    @property
    def resource_def(self):
        """Minimal representation of the resource"""
        fingerprint = layers.spec_hash(self.body["spec"])
        annotations = {
            f"{self.group}/openstack-controller-fingerprint": json.dumps(
                {
                    "osdpl_generation": self._get_osdpl().metadata[
                        "generation"
                    ],
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
                    if "hash_fields" not in meta:
                        m_ext["hash_fields"] = []
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
        LOG.info(f"Update {self.service} with {values}")

    def get_child_object(self, kind, name):
        return [
            child
            for child in self.child_objects
            if child.kind == kind and child.name == name
        ][0]

    def generate_child_object_hash(self, child_object, data):
        """Generate stable hash of child object

        The has takes into account hash_fileds and create stable hash
        by taking values from release.

        :param child_object: The child object
        :param: data: The whole helmbundle object data.
        :return: string with hash
        """

        def _get_release_values(data, chart_name):
            for release in data["spec"]["releases"]:
                if release["chart"].split("/")[1] == chart_name:
                    return release["values"]

        def _generate_child_object_hash(child_object, release_values):
            if not child_object.helmbundle_ext.hash_fields:
                return None

            hasher = hashlib.sha256()
            resource_hash_data = {}
            for field in child_object.helmbundle_ext.hash_fields:
                resource_hash_data[field] = [
                    match.value for match in parse(field).find(release_values)
                ]
            hasher.update(
                json.dumps(resource_hash_data, sort_keys=True).encode()
            )
            return hasher.hexdigest()

        release_values = _get_release_values(
            data, child_object.helmbundle_ext.chart
        )
        return _generate_child_object_hash(child_object, release_values)

    def generate_child_object_hashes(self, data):
        """Generate stable hash of child objects

        The has takes into account hash_fileds and create stable hash
        by taking values from release. Return json data with hashes.

        :param: data: The whole helmbundle object data.
        :return: json data with hash. Example
            {"<obj-kind Job|Deployment>": {
                "<job-name>": {
                    "hash": "<sha256hash>"
                    }
                }
            }
        """
        res = {}
        for child_object in self.child_objects:
            child_object_hash = self.generate_child_object_hash(
                child_object, data
            )
            child_hash = {
                child_object.helmbundle_ext.chart: {
                    child_object.kind: {
                        child_object.name: {"hash": child_object_hash}
                    }
                }
            }
            layers.merger.merge(res, child_hash)
        return res

    def get_child_object_current_hash(self, child_object):
        """Get currently defined child object hash stored
        in HelmBundle release annotations.

        :param child_object: Child object
        :returns: String with hash or None
        """
        hb = self._get_helmbundle()
        hb.reload()
        child_obj_metadata = json.loads(
            hb.annotations.get(
                f"{self.group}/openstack-controller-child-objects", "{}"
            )
        )
        return (
            child_obj_metadata.get(child_object.helmbundle_ext.chart, {})
            .get(child_object.kind, {})
            .get(child_object.name, {})
            .get("hash", None)
        )

    def is_child_object_hash_changed(self, child_object, data):
        """Check if object hash was changed

        :param child_object: Child object
        :param data: The whole helmbundle object data
        :returns: True when current hash not equal to hash in annotation
        """
        current_hash = self.get_child_object_current_hash(child_object)
        new_hash = self.generate_child_object_hash(child_object, data)

        return new_hash != current_hash

    def update_status(self, patch):
        self.osdpl.patch({"status": patch})

    async def cleanup_immutable_resources(
        self, new_obj, rendered_spec, force=False
    ):
        """
        Remove immmutable resources for helmbundle object when:
            1. The hash for release values fields used in child object
               is changed.
            2. The image of immutable object is changed
            3. The chart version for helmbundle is changed
            4. The force flag is set to True
        :param new_obj: the new helmbundle object representation
        :param rendered_spec: the current representation of helmbundle
        :param force: the flag to force remove all immutable objects that we know about.
        """
        old_obj = kube.resource(rendered_spec)
        old_obj.reload()

        to_cleanup = set()

        def _is_immutable_changed(image, chart):
            for old_release in old_obj.obj["spec"]["releases"]:
                if old_release["chart"].endswith(f"/{chart}"):
                    for new_release in new_obj.obj["spec"]["releases"]:
                        if new_release["chart"].endswith(f"/{chart}"):
                            old_version = old_release["version"]
                            new_version = new_release["version"]
                            old_image = old_release["values"]["images"][
                                "tags"
                            ].get(image)
                            new_image = new_release["values"]["images"][
                                "tags"
                            ][image]
                            if old_version != new_version:
                                return True
                            # When image name is changed it will not present in helmbundle object
                            # on deployed environmet. At the same time in current version of code
                            # we will use new name of image.
                            if old_image is None:
                                return True
                            if old_image != new_image:
                                return True

        for resource in self.child_objects:
            # NOTE(vsaienko): even the object is not immutable, it may have immutable fields.
            if self.is_child_object_hash_changed(resource, new_obj.obj):
                to_cleanup.add(resource)
            if resource.immutable:
                for image in resource.helmbundle_ext.images:
                    if force or _is_immutable_changed(
                        image, resource.helmbundle_ext.chart
                    ):
                        to_cleanup.add(resource)
                        # Break on first image match.
                        break

        LOG.info(f"Removing the following jobs: {to_cleanup}")
        tasks = set()
        for child_object in to_cleanup:
            tasks.add(child_object.purge())

        await asyncio.gather(*tasks)

    async def delete(self, *, body, meta, spec, logger, **kwargs):
        LOG.info(f"Deleting config for {self.service}")
        # TODO(e0ne): remove credentials of the deleted services
        data = self.resource_def
        kopf.adopt(data, self.osdpl.obj)
        obj = kube.resource(data)
        # delete the object, already non-existing are auto-handled
        obj.delete(propagation_policy="Foreground")
        LOG.info(f"{obj.kind} {obj.namespace}/{obj.name} deleted")
        # remove child reference from status
        self.update_status({"children": {obj.name: None}})
        kopf.info(
            body,
            reason="Delete",
            message=f"deleted {obj.kind} for {self.service}",
        )

    async def apply(self, event, **kwargs):
        # ensure child ref exists in the current status of osdpl object
        if self.resource_name not in self._get_osdpl().obj.get(
            "status", {}
        ).get("children", {}):
            status_patch = {"children": {self.resource_name: "Unknown"}}
            self.update_status(status_patch)
        LOG.info(f"Applying config for {self.service}")
        data = self.render()
        LOG.info(f"Config applied for {self.service}")

        # NOTE(pas-ha) this sets the parent refs in child
        # to point to our resource so that cascading delete
        # is handled by K8s itself
        kopf.adopt(data, self.osdpl.obj)
        helmbundle_obj = kube.resource(data)

        # apply state of the object
        if helmbundle_obj.exists():
            # Drop immutable resources (jobs) before changing theirs values.
            await self.cleanup_immutable_resources(helmbundle_obj, data)
            # TODO(pas-ha) delete jobs if image was changed
            helmbundle_obj.reload()
            helmbundle_obj.set_obj(data)
            helmbundle_obj.update()
            LOG.debug(
                f"{helmbundle_obj.kind} child is updated: %s",
                helmbundle_obj.obj,
            )
        else:
            if kwargs.get("helmobj_overrides", {}):
                self._helm_obj_override(
                    helmbundle_obj, kwargs["helmobj_overrides"]
                )
            helmbundle_obj.create()
            LOG.debug(
                f"{helmbundle_obj.kind} child is created: %s",
                helmbundle_obj.obj,
            )
        kopf.info(
            self.osdpl.obj,
            reason=event.capitalize(),
            message=f"{event}d {helmbundle_obj.kind} for {self.service}",
        )

    def _helm_obj_override(self, obj, overrides):
        for release in obj.obj["spec"]["releases"]:
            name = release["name"]
            if name in overrides:
                LOG.info(
                    f"Setting values {overrides[name]} for release {name}"
                )
                layers.merger.merge(release["values"], overrides[name])

    async def wait_service_healthy(self):
        for health_group in self.health_groups:
            LOG.info(f"Checking {health_group} health.")
            readiness_timeouts = (
                self.mspec.get("timeouts", {})
                .get("application_readiness", {})
                .get(health_group, {})
            )
            delay = readiness_timeouts.get(
                "delay", settings.OSCTL_WAIT_APPLICATION_READY_DELAY
            )
            timeout = readiness_timeouts.get(
                "timeout", settings.OSCTL_WAIT_APPLICATION_READY_TIMEOUT
            )
            await health.wait_application_ready(
                health_group, self.osdpl, delay=delay, timeout=timeout
            )

    async def _upgrade(self, event, **kwargs):
        pass

    async def upgrade(self, event, **kwargs):
        try:
            await self.wait_service_healthy()
            LOG.info(f"Upgrading {self.service} started.")
            await self._upgrade(event, **kwargs)

            await self.apply(event, **kwargs)
            # TODO(vsaienko): implement logic that will check that changes made in helmbundle
            # object were handled by tiller/helmcontroller
            # can be done only once https://mirantis.jira.com/browse/PRODX-2283 is implemented.
            await asyncio.sleep(settings.OSCTL_HELMBUNDLE_APPLY_DELAY)

            await self.wait_service_healthy()
        except Exception as e:
            # NOTE(vsaienko): always raise temporary error here, to ensure we retry upgrade from
            # failed service only. The whole upgrade restart might be done by restarting openstack
            # controller.
            LOG.exception(f"Got {e} when upgrading service {self.service}.")
            raise kopf.TemporaryError(f"Retrying to upgrade {self.service}")
        LOG.info(f"Upgrading {self.service} done")

    def template_args(self):
        secret = self._secret_class(self.namespace, self.service)
        credentials = secret.ensure()

        admin_creds = self._get_admin_creds()
        service_secrets = secrets.ServiceAccountsSecrets(
            self.namespace,
            self.service,
            self.service_accounts,
            self._required_accounts,
        )
        service_creds = service_secrets.ensure()

        template_args = {
            "credentials": credentials,
            "admin_creds": admin_creds,
            "service_creds": service_creds,
        }

        return template_args

    @layers.kopf_exception
    def render(self, openstack_version=""):
        if openstack_version:
            self.mspec["openstack_version"] = openstack_version
        template_args = self.template_args()
        data = layers.merge_all_layers(
            self.service,
            self.body,
            self.body["metadata"],
            self.mspec,
            self.logger,
            **template_args,
        )

        data.update(self.resource_def)

        child_hashes = self.generate_child_object_hashes(data)
        child_hashes_data = {
            "metadata": {
                "annotations": {
                    f"{self.group}/openstack-controller-child-objects": json.dumps(
                        child_hashes
                    )
                }
            }
        }
        layers.merger.merge(data, child_hashes_data)
        return data

    def get_chart_value_or_none(
        self, chart, path, openstack_version=None, default=None
    ):
        data = self.render(openstack_version)
        value = None
        for release in data["spec"]["releases"]:
            if release["chart"].endswith(f"/{chart}"):
                value = release["values"]
                try:
                    for path_link in path:
                        value = value[path_link]
                except KeyError:
                    return default
        return value

    def get_image(self, name, chart, openstack_version=None):
        return self.get_chart_value_or_none(
            chart,
            ["images", "tags", name],
            openstack_version=openstack_version,
        )

    @classmethod
    async def remove_node_from_scheduling(cls, node_metadata):
        pass

    @classmethod
    async def prepare_for_node_reboot(cls, node_metadata):
        pass

    @classmethod
    async def prepare_node_after_reboot(cls, node_metadata):
        pass

    @classmethod
    async def add_node_to_scheduling(cls, node_metadata):
        pass


class OpenStackService(Service):
    openstack_chart = None

    @property
    def health_groups(self):
        return [self.openstack_chart]

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


class OpenStackServiceWithCeph(OpenStackService):
    def ensure_ceph_secrets(self):
        self.create_ceph_secrets()

    def create_ceph_secrets(self):
        LOG.info("Waiting for ceph resources.")
        kube.wait_for_secret(
            settings.OSCTL_CEPH_SHARED_NAMESPACE,
            ceph_api.OPENSTACK_KEYS_SECRET,
        )
        oscp = ceph_api.get_os_ceph_params(secrets.get_secret_data)
        # TODO(vsaienko): the subset of secrets might be changed after
        # deployment. For example additional service is deployed,
        # we need to handle this.
        self.save_ceph_secrets(oscp)
        self.save_ceph_configmap(oscp)
        LOG.info("Ceph resources were created successfully.")

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
            srv_username = constants.OS_SERVICES_MAP.get(self.service)
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

    async def apply(self, event, **kwargs):
        # ensure child ref exists in the status
        self.ensure_ceph_secrets()
        await super().apply(event, **kwargs)

    def template_args(self):
        template_args = super().template_args()
        template_args.update(self.ceph_config())
        return template_args
