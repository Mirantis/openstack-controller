#    Copyright 2020 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import asyncio
import base64
import json

import kopf
import openstack
from openstack import exceptions
import pykube

from openstack_controller import ceph_api
from openstack_controller import constants
from openstack_controller import layers
from openstack_controller import kube
from openstack_controller import openstack_utils
from openstack_controller import secrets
from openstack_controller import settings
from openstack_controller import utils
from openstack_controller.services.base import (
    Service,
    OpenStackService,
    OpenStackServiceWithCeph,
)
from urllib.parse import urlsplit


LOG = utils.get_logger(__name__)

# INFRA SERVICES


class Ingress(Service):
    service = "ingress"

    @property
    def health_groups(self):
        return ["ingress"]


class Coordination(Service):
    service = "coordination"

    @property
    def health_groups(self):
        return ["etcd"]


class Redis(Service):
    service = "redis"
    group = "databases.spotahome.com"
    version = "v1"
    kind = "RedisFailover"
    namespace = settings.OSCTL_REDIS_NAMESPACE

    def template_args(self):
        redis_secret = secrets.RedisSecret(self.namespace)
        redis_creds = redis_secret.ensure()
        return {"redis_creds": redis_creds}

    def render(self, openstack_version=""):
        template_args = self.template_args()
        images = layers.render_artifacts(self.mspec)
        data = layers.render_service_template(
            self.service,
            self.body,
            self.body["metadata"],
            self.mspec,
            self.logger,
            images=images,
            **template_args,
        )
        data = layers.merge_service_layer(
            self.service,
            self.mspec,
            self.kind.lower(),
            data,
        )
        data.update(self.resource_def)

        return data

    async def apply(self, event, **kwargs):
        # ensure child ref exists in the current status of osdpl object
        self.set_children_status("Applying")
        LOG.info(f"Applying config for {self.service}")
        data = self.render()
        LOG.info(f"Config applied for {self.service}")

        # kopf.adopt is not used as kubernetes doesn't allow to use
        # cross namespace ownerReference
        data["apiVersion"] = "{0}/{1}".format(self.group, self.version)
        data["kind"] = self.kind
        data["name"] = "openstack-{0}".format(self.service)
        data["metadata"]["namespace"] = self.namespace
        redisfailover_obj = kube.resource(data)

        # apply state of the object
        if redisfailover_obj.exists():
            redisfailover_obj.reload()
            redisfailover_obj.set_obj(data)
            redisfailover_obj.update()
            LOG.debug(
                f"{redisfailover_obj.kind} child is updated: %s",
                redisfailover_obj.obj,
            )
        else:
            redisfailover_obj.create()
            LOG.debug(
                f"{redisfailover_obj.kind} child is created: %s",
                redisfailover_obj.obj,
            )
        kopf.info(
            self.osdpl.obj,
            reason=event.capitalize(),
            message=f"{event}d {redisfailover_obj.kind} for {self.service}",
        )
        self.set_children_status(True)


class MariaDB(Service):
    service = "database"

    @property
    def health_groups(self):
        return ["mysql"]

    _child_objects = {
        "mariadb": {
            "Job": {
                "openstack-mariadb-cluster-wait": {
                    "images": ["mariadb_scripted_test"],
                    "manifest": "job_cluster_wait",
                },
                "exporter-create-sql-user": {
                    "images": ["prometheus_create_mysql_user"],
                    # TODO(vsaienko): add support of hierarchical
                    "manifest": "",
                },
            }
        }
    }

    def template_args(self):
        admin_creds = self._get_admin_creds()
        galera_secret = secrets.GaleraSecret(self.namespace)
        galera_creds = galera_secret.ensure()
        return {"admin_creds": admin_creds, "galera_creds": galera_creds}


class Memcached(Service):
    service = "memcached"

    @property
    def health_groups(self):
        return ["memcached"]


class RabbitMQ(Service):
    service = "messaging"

    @property
    def health_groups(self):
        return ["rabbitmq"]

    _child_objects = {
        "rabbitmq": {
            "Job": {
                "openstack-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        }
    }

    def template_args(self):
        credentials = {}
        admin_creds = self._get_admin_creds()
        services = set(self.mspec["features"].get("services", [])) - set(
            ["tempest"]
        )
        for s in services:
            if s not in constants.OS_SERVICES_MAP:
                continue
            # NOTE(vsaienko): use secret_class from exact service as additional
            # passwords might be added like metadata password.
            secret = Service.registry[s]._secret_class(self.namespace, s)
            credentials[s] = secret.ensure()

        credentials["stacklight"] = secrets.StackLightPasswordSecret(
            self.namespace
        ).ensure()

        return {
            "services": services,
            "credentials": credentials,
            "admin_creds": admin_creds,
        }


class Aodh(OpenStackService):
    service = "alarming"
    openstack_chart = "aodh"


class Panko(OpenStackService):
    service = "event"
    openstack_chart = "panko"


class Ceilometer(OpenStackService):
    service = "metering"
    openstack_chart = "ceilometer"

    def template_args(self):
        t_args = super().template_args()
        panko_secret = secrets.OpenStackServiceSecret(self.namespace, "event")
        kube.wait_for_secret(self.namespace, panko_secret.secret_name)
        panko_creds = panko_secret.get()
        t_args["event_credentials"] = panko_creds
        return t_args


class Gnocchi(OpenStackService):
    service = "metric"
    openstack_chart = "gnocchi"

    def template_args(self):
        t_args = super().template_args()

        t_args["redis_namespace"] = settings.OSCTL_REDIS_NAMESPACE

        redis_secret = secrets.RedisSecret(settings.OSCTL_REDIS_NAMESPACE)
        kube.wait_for_secret(
            settings.OSCTL_REDIS_NAMESPACE, redis_secret.secret_name
        )
        redis_creds = redis_secret.get()
        t_args["redis_secret"] = redis_creds.password.decode()

        return t_args


# OPENSTACK SERVICES


class Barbican(OpenStackService):
    service = "key-manager"
    openstack_chart = "barbican"
    _secret_class = secrets.BarbicanSecret
    _child_objects = {
        "rabbitmq": {
            "Job": {
                "openstack-barbican-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        }
    }


class Cinder(OpenStackServiceWithCeph):
    service = "block-storage"
    openstack_chart = "cinder"
    _child_objects = {
        "cinder": {
            "Job": {
                "cinder-backup-storage-init": {
                    "images": ["cinder_backup_storage_init"],
                    "manifest": "job_backup_storage_init",
                },
                "cinder-create-internal-tenant": {
                    "images": ["ks_user"],
                    "manifest": "job_create_internal_tenant",
                },
                "cinder-storage-init": {
                    "images": ["cinder_storage_init"],
                    "manifest": "job_storage_init",
                },
                "cinder-db-sync-online": {
                    "images": ["cinder_db_sync_online"],
                    "manifest": "job_db_sync_online",
                },
                "cinder-db-sync": {
                    "images": ["cinder_db_sync"],
                    "manifest": "job_db_sync",
                },
            },
            "Deployment": {
                "cinder-api": {
                    "images": ["cinder_api"],
                    "manifest": "deployment_api",
                },
            },
            "StatefulSet": {
                "cinder-scheduler": {
                    "images": ["cinder_scheduler"],
                    "manifest": "statefulset_scheduler",
                },
                "cinder-volume": {
                    "images": ["cinder_volume"],
                    "manifest": "statefulset_volume",
                },
                "cinder-backup": {
                    "images": ["cinder_backup"],
                    "manifest": "statefulset_backup",
                },
            },
        },
        "rabbitmq": {
            "Job": {
                "openstack-cinder-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        },
    }

    @layers.kopf_exception
    async def _upgrade(self, event, **kwargs):
        upgrade_map = [
            ("Job", "cinder-db-sync"),
            ("StatefulSet", "cinder-scheduler"),
            ("StatefulSet", "cinder-volume"),
            ("StatefulSet", "cinder-backup"),
            ("Deployment", "cinder-api"),
            ("Job", "cinder-db-sync-online"),
        ]
        for kind, obj_name in upgrade_map:
            child_obj = self.get_child_object(kind, obj_name)
            if kind == "Job":
                await child_obj.purge()
            await child_obj.enable(self.openstack_version, True)


class Stepler(OpenStackService):
    service = "stepler"

    _child_objects = {
        "stepler": {
            "Job": {
                "stepler-run-tests": {
                    "images": ["stepler_run_tests"],
                    "manifest": "job_run_tests",
                },
                "stepler-bootstrap": {
                    "images": ["bootstrap"],
                    "manifest": "job_bootstrap",
                },
                "stepler-ks-user": {
                    "images": ["ks_user"],
                    "manifest": "job_ks_user",
                },
            }
        },
    }


class Designate(OpenStackService):
    service = "dns"
    backend_service = "powerdns"
    openstack_chart = "designate"
    _child_objects = {
        "designate": {
            "Job": {
                "designate-powerdns-db-init": {
                    "images": ["db_init"],
                    "manifest": "job_powerdns_db_init",
                },
                "designate-powerdns-db-sync": {
                    "images": ["powerdns_db_sync"],
                    "manifest": "job_powerdns_db_sync",
                },
            },
        },
        "rabbitmq": {
            "Job": {
                "openstack-designate-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        },
    }

    def template_args(self):
        t_args = super().template_args()
        power_dns_secret = secrets.PowerDNSSecret(self.namespace)
        credentials = power_dns_secret.ensure()
        t_args[self.backend_service] = credentials

        return t_args


class Glance(OpenStackServiceWithCeph):
    service = "image"
    openstack_chart = "glance"

    _child_objects = {
        "glance": {
            "Job": {
                "glance-metadefs-load": {
                    "images": ["glance_metadefs_load"],
                    "manifest": "job_metadefs_load",
                },
                "glance-storage-init": {
                    "images": ["glance_storage_init"],
                    "manifest": "job_storage_init",
                },
                "glance-db-expand": {
                    "images": ["glance_db_expand"],
                    "manifest": "job_db_expand",
                },
                "glance-db-migrate": {
                    "images": ["glance_db_migrate"],
                    "manifest": "job_db_migrate",
                },
                "glance-db-contract": {
                    "images": ["glance_db_contract"],
                    "manifest": "job_db_contract",
                },
            },
            "Deployment": {
                "glance-api": {
                    "images": ["glance_api"],
                    "manifest": "deployment_api",
                }
            },
        },
        "rabbitmq": {
            "Job": {
                "openstack-glance-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        },
    }

    @layers.kopf_exception
    async def _upgrade(self, event, **kwargs):
        upgrade_map = [
            ("Job", "glance-db-expand"),
            ("Job", "glance-db-migrate"),
            ("Deployment", "glance-api"),
            ("Job", "glance-db-contract"),
        ]
        for kind, obj_name in upgrade_map:
            child_obj = self.get_child_object(kind, obj_name)
            await child_obj.enable(self.openstack_version, True)


class Heat(OpenStackService):
    service = "orchestration"
    openstack_chart = "heat"
    _service_accounts = ["heat_trustee", "heat_stack_user"]
    _child_objects = {
        "heat": {
            "Job": {
                "heat-domain-ks-user": {
                    "images": ["ks_user"],
                    "manifest": "job_ks_user_domain",
                    "hash_fields": ["conf.*"],
                },
                "heat-trustee-ks-user": {
                    "images": ["ks_user"],
                    "manifest": "job_ks_user_trustee",
                },
                "heat-trusts": {
                    "images": ["ks_trusts"],
                    "manifest": "",
                    "hash_fields": ["conf.*"],
                },
                "heat-db-sync": {
                    "images": ["heat_db_sync"],
                    "manifest": "job_db_sync",
                },
            },
            "Deployment": {
                "heat-api": {
                    "images": ["heat_api"],
                    "manifest": "deployment_api",
                },
                "heat-cfn": {
                    "images": ["heat_cfn"],
                    "manifest": "deployment_cfn",
                },
                "heat-engine": {
                    "images": ["heat_engine"],
                    "manifest": "deployment_engine",
                },
            },
        },
        "rabbitmq": {
            "Job": {
                "openstack-heat-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        },
    }

    @layers.kopf_exception
    async def _upgrade(self, event, **kwargs):
        upgrade_map = [
            ("Job", "heat-db-sync"),
            ("Deployment", "heat-api"),
            ("Deployment", "heat-cfn"),
            ("Deployment", "heat-engine"),
        ]

        extra_values = {
            "endpoints": {
                "oslo_messaging": {
                    "path": self.get_chart_value_or_none(
                        self.openstack_chart,
                        ["endpoints", "oslo_messaging", "path"],
                        self.openstack_version,
                    )
                }
            }
        }

        # NOTE(vsaienko): we update endpoints which update configmap-etc hash
        # so all heat jobs are affected. We need to purge them before doing
        # first apply.
        for resource in self.child_objects:
            if resource.immutable:
                await resource.purge()

        for kind, obj_name in upgrade_map:
            child_obj = self.get_child_object(kind, obj_name)
            if kind == "Job":
                await child_obj.purge()
            await child_obj.enable(self.openstack_version, True, extra_values)


class Horizon(OpenStackService):
    service = "dashboard"
    openstack_chart = "horizon"
    _secret_class = secrets.HorizonSecret

    @property
    def _child_generic_objects(self):
        return {"horizon": {"job_db_init", "job_db_sync", "job_db_drop"}}

    def template_args(self):
        t_args = super().template_args()

        kube.wait_for_secret(
            settings.OSCTL_CEPH_SHARED_NAMESPACE,
            ceph_api.OPENSTACK_KEYS_SECRET,
        )
        rgw_internal_cacert = secrets.get_secret_data(
            settings.OSCTL_CEPH_SHARED_NAMESPACE,
            ceph_api.OPENSTACK_KEYS_SECRET,
        ).get("rgw_internal_cacert")
        if rgw_internal_cacert:
            rgw_internal_cacert = base64.b64decode(
                rgw_internal_cacert
            ).decode()
            t_args["rgw_internal_cacert"] = rgw_internal_cacert

        return t_args


class Ironic(OpenStackService):
    service = "baremetal"
    openstack_chart = "ironic"

    @property
    def _required_accounts(self):
        r_accounts = {"networking": ["neutron"], "image": ["glance"]}
        return r_accounts

    _child_objects = {
        "ironic": {
            "Job": {
                "ironic-manage-networks": {
                    "images": ["ironic_manage_networks"],
                    "manifest": "job_manage_networks",
                }
            }
        },
        "rabbitmq": {
            "Job": {
                "openstack-ironic-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        },
    }


class Keystone(OpenStackService):
    service = "identity"
    openstack_chart = "keystone"

    @property
    def _child_generic_objects(self):
        return {
            "keystone": {
                "job_db_init",
                "job_db_sync",
                "job_db_drop",
                "job_bootstrap",
            }
        }

    _child_objects = {
        "keystone": {
            "Job": {
                "keystone-domain-manage": {
                    "images": ["keystone_domain_manage"],
                    "manifest": "job_domain_manage",
                    "hash_fields": ["conf.*"],
                },
                "keystone-fernet-setup": {
                    "images": ["keystone_fernet_setup"],
                    "manifest": "job_fernet_setup",
                    "hash_fields": ["conf.*"],
                },
                "keystone-credential-setup": {
                    "images": ["keystone_credential_setup"],
                    "manifest": "job_credential_setup",
                    "hash_fields": ["conf.*"],
                },
                "keystone-db-sync-expand": {
                    "images": ["keystone_db_sync_expand"],
                    "manifest": "job_db_sync_expand",
                },
                "keystone-db-sync-migrate": {
                    "images": ["keystone_db_sync_migrate"],
                    "manifest": "job_db_sync_migrate",
                },
                "keystone-db-sync-contract": {
                    "images": ["keystone_db_sync_contract"],
                    "manifest": "job_db_sync_contract",
                },
                "keystone-federations-create": {
                    "images": ["keystone_federations_create"],
                    "manifest": "job_federations_create",
                },
            },
            "Deployment": {
                "keystone-api": {
                    "images": ["keystone_api"],
                    "manifest": "deployment_api",
                }
            },
        },
        "rabbitmq": {
            "Job": {
                "openstack-keystone-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                    "hash_fields": ["endpoints.oslo_messaging.*"],
                }
            }
        },
    }

    def _get_keycloak_args(self):
        args = {}
        keycloak_salt = secrets.KeycloakSecret(self.namespace)
        args["oidc_crypto_passphrase"] = keycloak_salt.ensure().passphrase

        # Create openstack IAM shared secret
        oidc_settings = (
            self.mspec.get("features", {})
            .get("keystone", {})
            .get("keycloak", {})
            .get("oidc", {})
        )
        public_domain = self.mspec["public_domain_name"]
        keystone_base = f"https://keystone.{public_domain}"
        redirect_uris_default = [
            f"{keystone_base}/v3/OS-FEDERATION/identity_providers/keycloak/protocols/mapped/auth",
            f"{keystone_base}/v3/auth/OS-FEDERATION/websso/",
            f"{keystone_base}/v3/auth/OS-FEDERATION/identity_providers/keycloak/protocols/mapped/websso/",
            f"https://horizon.{public_domain}/*",
        ]
        redirect_uris = oidc_settings.get(
            "OIDCRedirectURI", redirect_uris_default
        )

        iam_secret = secrets.IAMSecret(self.namespace)
        iam_data = secrets.OpenStackIAMData(
            clientId=oidc_settings.get("OIDCClientID", "os"),
            redirectUris=redirect_uris,
        )
        iam_secret.save(iam_data)

        # Get IAM CA certificate
        oidc_ca_secret = oidc_settings.get("oidcCASecret")
        if oidc_ca_secret:
            kube.wait_for_secret(
                self.namespace,
                oidc_ca_secret,
            )
            args["oidc_ca"] = base64.b64decode(
                secrets.get_secret_data(
                    self.namespace,
                    oidc_ca_secret,
                )["ca-cert.pem"]
            ).decode()
        return args

    def _get_object_storage_args(self):
        args = {}
        # Get internal RGW secret
        kube.wait_for_secret(
            settings.OSCTL_CEPH_SHARED_NAMESPACE,
            ceph_api.OPENSTACK_KEYS_SECRET,
        )
        rgw_internal_cacert = secrets.get_secret_data(
            settings.OSCTL_CEPH_SHARED_NAMESPACE,
            ceph_api.OPENSTACK_KEYS_SECRET,
        ).get("rgw_internal_cacert")
        if rgw_internal_cacert:
            rgw_internal_cacert = base64.b64decode(
                rgw_internal_cacert
            ).decode()
            args["rgw_internal_cacert"] = rgw_internal_cacert
        return args

    def _get_keystone_args(self):
        args = {}
        # Ensure the secrets with credentials/fernet keys exists
        fernet_secret_name = "keystone-fernet-data"
        credentials_secret_name = "keystone-credential-data"
        args["fernet_secret_name"] = fernet_secret_name
        args["credentials_secret_name"] = credentials_secret_name

        for secret_names in [
            ("keystone-fernet-keys", fernet_secret_name),
            ("keystone-credential-keys", credentials_secret_name),
        ]:
            LOG.info(f"Handling secret {secret_names}")
            old_secret, new_secret = secret_names

            try:
                kube.find(
                    kube.Secret,
                    name=new_secret,
                    namespace=self.namespace,
                    silent=False,
                )
            except pykube.exceptions.ObjectDoesNotExist:
                LOG.debug(f"The {new_secret} does not exists")
                data = {}
                try:
                    old_secret_obj = kube.find(
                        kube.Secret,
                        name=old_secret,
                        namespace=self.namespace,
                        silent=False,
                    )
                    data = old_secret_obj.obj["data"]
                except pykube.exceptions.ObjectDoesNotExist:
                    LOG.debug(f"The {old_secret} does not exists")

                kube.save_secret_data(
                    namespace=self.namespace, name=new_secret, data=data
                )
                LOG.debug(
                    f"Secret {new_secret} has been created successfully."
                )
        return args

    def template_args(self):
        t_args = super().template_args()
        t_args.update(self._get_keystone_args())

        keycloak_enabled = (
            self.mspec.get("features", {})
            .get("keystone", {})
            .get("keycloak", {})
            .get("enabled", False)
        )

        if keycloak_enabled:
            t_args.update(self._get_keycloak_args())

        if "object-storage" in self.mspec.get("features", {}).get(
            "services", []
        ):
            t_args.update(self._get_object_storage_args())

        return t_args

    @layers.kopf_exception
    async def _upgrade(self, event, **kwargs):
        upgrade_map = [
            ("Job", "keystone-db-sync-expand"),
            ("Job", "keystone-db-sync-migrate"),
            ("Deployment", "keystone-api"),
            ("Job", "keystone-db-sync-contract"),
        ]
        for kind, obj_name in upgrade_map:
            child_obj = self.get_child_object(kind, obj_name)
            await child_obj.enable(self.openstack_version, True)


class Neutron(OpenStackService):
    service = "networking"
    openstack_chart = "neutron"
    _secret_class = secrets.NeutronSecret

    @property
    def _required_accounts(self):
        r_accounts = {"dns": ["designate"]}
        compute_accounts = ["nova"]
        if self.openstack_version in [
            "queens",
            "rocky",
        ]:
            compute_accounts.append("placement")
        else:
            r_accounts["placement"] = ["placement"]

        r_accounts["compute"] = compute_accounts
        services = self.mspec["features"]["services"]
        if "baremetal" in services:
            r_accounts["baremetal"] = ["ironic"]
        return r_accounts

    def template_args(self):
        t_args = super().template_args()

        ngs_ssh_keys = {}
        if "baremetal" in self.mspec["features"]["services"]:
            for device in (
                self.mspec["features"]
                .get("neutron", {})
                .get("baremetal", {})
                .get("ngs", {})
                .get("devices", [])
            ):
                if "ssh_private_key" in device:
                    ngs_ssh_keys[f"{device['name']}_ssh_private_key"] = device[
                        "ssh_private_key"
                    ]
        if ngs_ssh_keys:
            ngs_secret = secrets.NgsSSHSecret(self.namespace)
            ngs_secret.save(ngs_ssh_keys)

        # Get Tungsten Fabric API endpoint
        if (
            utils.get_in(self.mspec["features"], ["neutron", "backend"])
            == "tungstenfabric"
        ):
            kube.wait_for_secret(
                constants.OPENSTACK_TF_SHARED_NAMESPACE,
                constants.TF_OPENSTACK_SECRET,
            )
            tf_secret = secrets.get_secret_data(
                constants.OPENSTACK_TF_SHARED_NAMESPACE,
                constants.TF_OPENSTACK_SECRET,
            )

            tf_api_keys = ["tf_api_service", "tf_api_port"]
            if all([k in tf_secret for k in tf_api_keys]):
                t_args.update(
                    {
                        key: base64.b64decode(tf_secret[key]).decode()
                        for key in tf_api_keys
                    }
                )
        if (
            utils.get_in(
                self.mspec["features"], ["neutron", "bgpvpn", "enabled"]
            )
            == True
            and utils.get_in(
                self.mspec["features"], ["neutron", "bgpvpn", "peers"]
            )
            == None
        ):
            neighbors_secret = secrets.BGPVPNSecret()
            peers = []
            # NOTE(vsaienko) we deploy frr with networking helmbundle, so render
            # first with empty peers, which will be updated once frr chart create
            # secret
            if neighbors_secret.kube_obj.exists():
                peers = neighbors_secret.get_peer_ips()
            self.mspec["features"]["neutron"]["bgpvpn"]["peers"] = peers

        return t_args

    @property
    def health_groups(self):
        health_groups = [self.openstack_chart]
        if (
            utils.get_in(self.mspec["features"], ["neutron", "backend"])
            != "tungstenfabric"
        ):
            health_groups.append("openvswitch")

        return health_groups

    @property
    def _child_objects(self):
        neutron_jobs = {}

        if (
            utils.get_in(self.mspec["features"], ["neutron", "backend"])
            == "tungstenfabric"
        ):
            neutron_jobs = {
                "tungstenfabric-ks-service": {
                    "images": ["ks_service"],
                    "manifest": "job_ks_service",
                },
                "tungstenfabric-ks-endpoints": {
                    "images": ["ks_endpoints"],
                    "manifest": "job_ks_endpoints",
                },
            }

        return {
            "neutron": {
                "Job": neutron_jobs,
            },
            "rabbitmq": {
                "Job": {
                    "openstack-neutron-rabbitmq-cluster-wait": {
                        "images": ["rabbitmq_scripted_test"],
                        "manifest": "job_cluster_wait",
                        "hash_fields": ["endpoints.oslo_messaging.*"],
                    }
                }
            },
        }

    async def apply(self, event, **kwargs):
        neutron_features = self.mspec["features"].get("neutron", {})
        if neutron_features.get("backend", "") == "tungstenfabric":
            ssl_public_endpoints = (
                self.mspec["features"]
                .get("ssl", {})
                .get("public_endpoints", {})
            )
            b64encode = lambda v: base64.b64encode(v.encode()).decode()
            secret_data = {
                "tunnel_interface": b64encode(
                    neutron_features.get("tunnel_interface", "")
                ),
                "public_domain": b64encode(self.mspec["public_domain_name"]),
                "certificate_authority": b64encode(
                    ssl_public_endpoints.get("ca_cert")
                ),
                "certificate": b64encode(ssl_public_endpoints.get("api_cert")),
                "private_key": b64encode(ssl_public_endpoints.get("api_key")),
                "ingress_namespace_class": b64encode(
                    utils.get_in(
                        self.mspec["services"],
                        [
                            "ingress",
                            "ingress",
                            "values",
                            "deployment",
                            "cluster",
                            "class",
                        ],
                        "nginx-cluster",
                    )
                ),
            }

            nodes = {}
            if self.mspec.get("nodes"):
                for label_key in self.mspec["nodes"]:
                    if utils.get_in(
                        self.mspec["nodes"][label_key], ["features", "neutron"]
                    ):
                        nodes[label_key] = utils.get_in(
                            self.mspec["nodes"][label_key],
                            ["features", "neutron"],
                        )
            secret_data["nodes"] = b64encode(json.dumps(nodes))

            tfs = secrets.TungstenFabricSecret()
            tfs.save(secret_data)

        await super().apply(event, **kwargs)


class Nova(OpenStackServiceWithCeph):
    service = "compute"
    openstack_chart = "nova"

    @property
    def _service_accounts(self):
        s_accounts = []
        if self.openstack_version in [
            "queens",
            "rocky",
        ]:
            s_accounts.append("placement")
        return s_accounts

    @property
    def _required_accounts(self):
        r_accounts = {"networking": ["neutron"]}
        if self.openstack_version not in [
            "queens",
            "rocky",
        ]:
            r_accounts["placement"] = ["placement"]
        services = self.mspec["features"]["services"]
        if "baremetal" in services:
            r_accounts["baremetal"] = ["ironic"]
        return r_accounts

    @property
    def _child_objects(self):
        nova_jobs = {
            "nova-cell-setup": {
                "images": ["nova_cell_setup", "nova_cell_setup_init"],
                "manifest": "job_cell_setup",
            },
            "nova-db-sync-api": {
                "images": ["nova_db_sync_api"],
                "manifest": "job_db_sync_api",
            },
            "nova-db-sync-db": {
                "images": ["nova_db_sync_db"],
                "manifest": "job_db_sync_db",
            },
            "nova-db-sync-online": {
                "images": ["nova_db_sync_online"],
                "manifest": "job_db_sync_online",
            },
            "nova-db-sync": {
                "images": ["nova_db_sync"],
                "manifest": "job_db_sync",
                "hash_fields": [
                    "endpoints.oslo_messaging.*",
                    "endpoints.oslo_db.*",
                ],
            },
        }
        nova_deployments = {}
        nova_secrets = {}
        nova_ingresses = {}
        nova_services = {}
        if self.openstack_version in [
            "queens",
            "rocky",
            # Consider placement resources as childs in stein too,
            # needed for upgrade from rocky to stein. The effect is
            # that when nova is upgraded from rocky to stein or
            # from stein to train it will remove placement-ks-*
            # jobs. But there is no negative effect on placement
            # upgrade result.
            "stein",
        ]:
            nova_jobs = {
                **nova_jobs,
                "placement-ks-user": {
                    "images": ["ks_user"],
                    "manifest": "job_ks_placement_user",
                },
                "placement-ks-service": {
                    "images": ["ks_service"],
                    "manifest": "job_ks_placement_service",
                },
                "placement-ks-endpoints": {
                    "images": ["ks_endpoints"],
                    "manifest": "job_ks_placement_endpoints",
                },
            }
            nova_deployments = {
                **nova_deployments,
                "nova-placement-api": {
                    "manifest": "deployment_placement",
                    "images": [],
                },
            }
            nova_secrets = {
                **nova_secrets,
                "placement-tls-public": {
                    "manifest": "ingress_placement",
                    "images": [],
                },
            }
            nova_services = {
                **nova_services,
                "placement-api": {
                    "manifest": "service_placement",
                    "images": [],
                },
                "placement": {
                    "manifest": "service_ingress_placement",
                    "images": [],
                },
            }
            nova_ingresses = {
                **nova_ingresses,
                "placement": {
                    "manifest": "ingress_placement",
                    "images": [],
                },
            }
        return {
            "nova": {
                "Job": nova_jobs,
                "Secret": nova_secrets,
                "Deployment": nova_deployments,
                "Service": nova_services,
                "Ingress": nova_ingresses,
            },
            "rabbitmq": {
                "Job": {
                    "openstack-nova-rabbitmq-cluster-wait": {
                        "images": ["rabbitmq_scripted_test"],
                        "manifest": "job_cluster_wait",
                        "hash_fields": ["endpoints.oslo_messaging.*"],
                    }
                }
            },
        }

    def template_args(self):
        t_args = super().template_args()

        ssh_secret = secrets.SSHSecret(self.namespace, "nova")
        t_args["ssh_credentials"] = ssh_secret.ensure()

        neutron_secret = secrets.NeutronSecret(self.namespace, "networking")
        kube.wait_for_secret(self.namespace, neutron_secret.secret_name)
        neutron_creds = neutron_secret.get()

        t_args["metadata_secret"] = neutron_creds.metadata_secret

        neutron_features = self.mspec["features"].get("neutron", {})

        # Read secret from shared namespace with TF deployment to
        # get value of vrouter port for setting it as env variable
        # in nova-compute container
        if neutron_features.get("backend", "") == "tungstenfabric":
            kube.wait_for_secret(
                constants.OPENSTACK_TF_SHARED_NAMESPACE,
                constants.TF_OPENSTACK_SECRET,
            )
            vrouter_port = base64.b64decode(
                secrets.get_secret_data(
                    constants.OPENSTACK_TF_SHARED_NAMESPACE,
                    constants.TF_OPENSTACK_SECRET,
                )["vrouter_port"]
            ).decode()

            t_args["vrouter_port"] = vrouter_port

        return t_args

    @layers.kopf_exception
    async def _upgrade(self, event, **kwargs):
        upgrade_map = [
            ("Job", "nova-db-sync-api"),
            ("Job", "nova-db-sync-db"),
            ("Job", "nova-db-sync"),
        ]
        for kind, obj_name in upgrade_map:
            child_obj = self.get_child_object(kind, obj_name)
            await child_obj.purge()
            await child_obj.enable(self.openstack_version, True)

    @classmethod
    async def remove_node_from_scheduling(cls, node_metadata):
        node_name = node_metadata["name"]
        openstack_connection = await openstack_utils.get_openstack_connection()
        try:
            target_service = openstack_utils.get_single_service(
                openstack_connection, host=node_name
            )
            if target_service and target_service["state"] == "up":
                openstack_connection.compute.disable_service(
                    target_service["id"], node_name, "nova-compute"
                )

                def wait_for_service_disabled():
                    service = openstack_utils.get_single_service(
                        openstack_connection, host=node_name
                    )
                    if service and service["status"] == "disabled":
                        return service

                try:
                    await asyncio.wait_for(
                        utils.async_retry(wait_for_service_disabled),
                        timeout=60,
                    )
                except asyncio.TimeoutError:
                    raise kopf.TemporaryError(
                        "Can not remove host from scheduling as "
                        "compute service can not be disabled"
                    )
        except exceptions.SDKException as e:
            LOG.error(f"Cannot execute openstack commands, error: {e}")
            raise kopf.TemporaryError(
                "Can not disable compute service on a host to be deleted"
            )

    @classmethod
    async def prepare_for_node_reboot(cls, node_metadata):
        node_name = node_metadata["name"]
        openstack_connection = await openstack_utils.get_openstack_connection()
        try:
            target_service = openstack_utils.get_single_service(
                openstack_connection, host=node_name
            )
            if target_service and target_service["state"] == "up":
                migrate_func = openstack_connection.compute.live_migrate_server
            else:
                if not settings.OSCTL_ALLOW_EVACUATION:
                    raise kopf.PermanentError(
                        "Can not live migrate instances off of host being "
                        "deleted as it is down"
                    )
                migrate_func = openstack_connection.compute.evacuate_server
            servers_to_migrate = list(
                openstack_connection.compute.servers(
                    details=False, all_projects=True, host=node_name
                )
            )
            await openstack_utils.migrate_servers(
                openstack_connection=openstack_connection,
                migrate_func=migrate_func,
                servers=servers_to_migrate,
                migrating_off=node_name,
                concurrency=settings.OSCTL_MIGRATE_CONCURRENCY,
            )
        except exceptions.SDKException as e:
            LOG.error(f"Cannot execute openstack commands, error: {e}")
            raise kopf.TemporaryError(
                "Can not move instances off of deleted host"
            )

    @classmethod
    async def prepare_node_after_reboot(cls, node_metadata):
        node_name = node_metadata["name"]
        openstack_connection = await openstack_utils.get_openstack_connection()
        try:

            def wait_for_service_found():
                return openstack_utils.get_single_service(
                    openstack_connection, host=node_name
                )

            try:
                await asyncio.wait_for(
                    utils.async_retry(wait_for_service_found),
                    timeout=300,
                )
            except asyncio.TimeoutError:
                raise kopf.TemporaryError(
                    "compute service not found, can not discover the newly "
                    "added compute host"
                )
        except openstack.exceptions.SDKException as e:
            LOG.error(f"Cannot execute openstack commands, error: {e}")
            raise kopf.TemporaryError(
                "can not discover the newly added compute host"
            )
        try:
            osdpl = kube.resource_list(
                kube.OpenStackDeployment,
                None,
                settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
            ).get()
        except Exception as e:
            LOG.error(f"Can not find OpenStackDeployment, error is: {e}")
            raise kopf.PermanentError(
                "OpenStackDeployment not found, can not discover the newly "
                "added compute host"
            )
        job = await openstack_utils.find_nova_cell_setup_cron_job(
            node_uid=node_metadata["uid"]
        )
        kopf.adopt(job, osdpl.obj)
        kube_job = kube.Job(kube.api, job)
        try:
            try:
                kube_job.create()
                # TODO(vdrok): wait for job completion
            except pykube.exceptions.HTTPError as e:
                if e.code == 409:
                    # Job already exists, recreate it just in case
                    kube_job.delete()
                    raise kopf.TemporaryError(
                        "Nova cell-setup job is being deleted, will retry "
                        "in a while"
                    )
                else:
                    raise
        except pykube.exceptions.HTTPError as e:
            LOG.error(
                f"Cannot create job {job['metadata']['name']}, error: {e}"
            )
            raise kopf.PermanentError(
                f"Cannot create job {job['metadata']['name']}"
            )

    @classmethod
    async def add_node_to_scheduling(cls, node_metadata):
        node_name = node_metadata["name"]
        openstack_connection = await openstack_utils.get_openstack_connection()
        try:
            service = openstack_utils.get_single_service(
                openstack_connection, host=node_name
            )
            # Enable service, in case this is a compute that was previously
            # removed and now is being added back
            openstack_connection.compute.enable_service(
                service["id"], node_name, "nova-compute"
            )

            def wait_for_service_enabled():
                service = openstack_utils.get_single_service(
                    openstack_connection, host=node_name
                )
                if service and service["status"] == "enabled":
                    return service

            try:
                await asyncio.wait_for(
                    utils.async_retry(wait_for_service_enabled),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                raise kopf.TemporaryError(
                    "compute service can not be enabled, can not bring node "
                    "back to scheduling"
                )
        except openstack.exceptions.SDKException as e:
            LOG.error(f"Cannot execute openstack commands, error: {e}")
            raise kopf.TemporaryError("can not bring node back to scheduling")


class Placement(OpenStackService):
    service = "placement"
    openstack_chart = "placement"

    @property
    def _child_generic_objects(self):
        return {
            "placement": {
                "job_db_init",
                "job_db_sync",
                "job_db_drop",
                "job_ks_endpoints",
                "job_ks_service",
                "job_ks_user",
            }
        }

    @layers.kopf_exception
    async def upgrade(self, event, **kwargs):
        LOG.info(f"Upgrading {self.service} started.")
        # NOTE(mkarpin): skip health check for stein release,
        # as this is first release where placement is added
        if self.body["spec"]["openstack_version"] == "stein":
            self._child_objects = {
                "placement": {
                    "Job": {
                        "placement-db-nova-migrate-placement": {
                            "images": ["placement_db_nova_migrate_placement"],
                            "manifest": "job_db_nova_migrate_placement",
                        },
                    },
                },
            }
            upgrade_map = [
                ("Deployment", "nova-placement-api"),
                ("Job", "placement-ks-user"),
                ("Job", "placement-ks-service"),
                ("Job", "placement-ks-endpoints"),
                ("Service", "placement"),
                ("Service", "placement-api"),
                ("Secret", "placement-tls-public"),
                ("Ingress", "placement"),
            ]
            compute_service_instance = Service.registry["compute"](
                self.body, self.logger
            )
            try:
                LOG.info(
                    f"Disabling Nova child objects related to {self.service}."
                )
                kwargs["helmobj_overrides"] = {
                    "openstack-placement": {
                        "manifests": {"job_db_nova_migrate_placement": True}
                    }
                }
                for kind, obj_name in upgrade_map:
                    child_obj = compute_service_instance.get_child_object(
                        kind, obj_name
                    )
                    await child_obj.disable(wait_completion=True)
                LOG.info(
                    f"{self.service} database migration will be performed."
                )
                await self.apply(event, **kwargs)
                # TODO(vsaienko): implement logic that will check that changes made in helmbundle
                # object were handled by tiller/helmcontroller
                # can be done only once https://mirantis.jira.com/browse/PRODX-2283 is implemented.
                await asyncio.sleep(settings.OSCTL_HELMBUNDLE_APPLY_DELAY)
                await self.wait_service_healthy()
                # NOTE(mkarpin): db sync job should be cleaned up after upgrade and before apply
                # because placement_db_nova_migrate_placement job is in dynamic dependencies
                # for db sync job, during apply it will be removed
                LOG.info(f"Cleaning up database migration jobs")
                await self.get_child_object("Job", "placement-db-sync").purge()
                # Recreate placement-db-sync without nova_migrate_placement dependency
                kwargs.pop("helmobj_overrides")
                await self.apply(event, **kwargs)
            except Exception as e:
                # NOTE(mkarpin): in case something went wrong during placement migration
                # we need to cleanup all child objects related to placement
                # because disabling procedure  in next retry will never succeed, because
                # nova release already have all objects disabled.
                for kind, obj_name in upgrade_map:
                    child_obj = compute_service_instance.get_child_object(
                        kind, obj_name
                    )
                    await child_obj.purge()
                raise kopf.TemporaryError(f"{e}") from e
            LOG.info(f"Upgrading {self.service} done")
        else:
            await super().upgrade(event, **kwargs)


class Octavia(OpenStackService):
    service = "load-balancer"
    openstack_chart = "octavia"

    @property
    def _child_objects(self):
        ch_objects = {
            "octavia": {
                "Job": {
                    "octavia-create-resources": {
                        "images": ["create_resources"],
                        "manifest": "job_create_resources",
                        "hash_fields": [
                            "octavia.settings.amphora_image_url",
                            "network.proxy.*",
                        ],
                    }
                }
            },
            "rabbitmq": {
                "Job": {
                    "openstack-octavia-rabbitmq-cluster-wait": {
                        "images": ["rabbitmq_scripted_test"],
                        "manifest": "job_cluster_wait",
                        "hash_fields": ["endpoints.oslo_messaging.*"],
                    }
                }
            },
        }

        if self.openstack_version not in ["queens", "rocky", "stein", "train"]:
            ch_objects["octavia"]["Job"]["octavia-db-sync-persistence"] = {
                "images": ["octavia_db_sync_persistence"],
                "manifest": "job_db_sync_persistence",
            }
        return ch_objects

    def template_args(self):
        t_args = super().template_args()
        cert_secret = secrets.SignedCertificateSecret(
            self.namespace, "octavia"
        )
        cert_secret.ensure()
        ssh_secret = secrets.SSHSecret(self.namespace, self.service)
        t_args["ssh_credentials"] = ssh_secret.ensure()

        if "redis" in self.mspec["features"]["services"]:
            t_args["redis_namespace"] = settings.OSCTL_REDIS_NAMESPACE

            redis_secret = secrets.RedisSecret(settings.OSCTL_REDIS_NAMESPACE)
            kube.wait_for_secret(
                settings.OSCTL_REDIS_NAMESPACE, redis_secret.secret_name
            )
            redis_creds = redis_secret.get()
            t_args["redis_secret"] = redis_creds.password.decode()
        return t_args


class RadosGateWay(Service):
    service = "object-storage"

    _child_objects = {
        "ceph-rgw": {
            "Job": {
                "ceph-ks-endpoints": {
                    "images": ["ks_endpoints"],
                    "manifest": "job_ks_endpoints",
                    "hash_fields": ["endpoints.*"],
                },
                "ceph-ks-service": {
                    "images": ["ks_service"],
                    "manifest": "job_ks_service",
                },
                "ceph-rgw-ks-user": {
                    "images": ["ks_user"],
                    "manifest": "job_ks_user",
                },
            }
        }
    }

    # override health groups to skip wait for healthy service check
    # as ceph rgw contain only jobs
    @property
    def health_groups(self):
        return []

    def template_args(self):
        t_args = super().template_args()

        auth_url = "https://keystone." + self.mspec["public_domain_name"]
        ssl_public_endpoints = self.mspec["features"]["ssl"][
            "public_endpoints"
        ]
        # NOTE(vsaienko): share date with ceph first so it can construct correct
        # public endpoint
        for service_cred in t_args["service_creds"]:
            if service_cred.account == "ceph-rgw":
                rgw_creds = {
                    "auth_url": auth_url,
                    "default_domain": "default",
                    "interface": "public",
                    "password": service_cred.password,
                    "project_domain_name": "service",
                    "project_name": "service",
                    "region_name": "RegionOne",
                    "user_domain_name": "default",
                    "username": service_cred.username,
                    "public_domain": self.mspec["public_domain_name"],
                    "ca_cert": ssl_public_endpoints["ca_cert"],
                    "tls_crt": ssl_public_endpoints["api_cert"],
                    "tls_key": ssl_public_endpoints["api_key"],
                }

                # encode values from rgw_creds
                for key in rgw_creds.keys():
                    rgw_creds[key] = base64.b64encode(
                        rgw_creds[key].encode()
                    ).decode()

                os_rgw_creds = ceph_api.OSRGWCreds(**rgw_creds)

                ceph_api.set_os_rgw_creds(
                    os_rgw_creds=os_rgw_creds,
                    save_secret=kube.save_secret_data,
                )
                LOG.info(
                    "Secret with RGW creds has been created successfully."
                )
                break

        kube.wait_for_secret(
            settings.OSCTL_CEPH_SHARED_NAMESPACE,
            ceph_api.OPENSTACK_KEYS_SECRET,
        )

        for rgw_key in ["rgw_internal", "rgw_external"]:
            rgw_url = base64.b64decode(
                secrets.get_secret_data(
                    settings.OSCTL_CEPH_SHARED_NAMESPACE,
                    ceph_api.OPENSTACK_KEYS_SECRET,
                ).get(rgw_key)
            ).decode()

            urlparsed = urlsplit(rgw_url)
            rgw_port = urlparsed.port
            if not rgw_port:
                if urlparsed.scheme == "http":
                    rgw_port = "80"
                if urlparsed.scheme == "https":
                    rgw_port = "443"

            t_args[rgw_key] = {
                "host": urlparsed.hostname,
                "port": rgw_port,
                "scheme": urlparsed.scheme,
            }

        return t_args


class Tempest(Service):
    service = "tempest"

    _child_objects = {
        "tempest": {
            "Job": {
                "openstack-tempest-run-tests": {
                    "images": ["tempest_run_tests", "tempest-uuids-init"],
                    "manifest": "job_run_tests",
                },
                "tempest-bootstrap": {
                    "images": ["bootstrap"],
                    "manifest": "job_bootstrap",
                },
                "tempest-image-repo-sync": {
                    "images": ["image_repo_sync"],
                    "manifest": "job_image_repo_sync",
                },
                "tempest-ks-user": {
                    "images": ["ks_user"],
                    "manifest": "job_ks_user",
                },
            }
        },
    }

    def template_args(self):
        template_args = super().template_args()

        helmbundles_body = {}
        for s in set(self.mspec["features"]["services"]) - {
            "tempest",
            "redis",
        }:
            service_template_args = Service.registry[s](
                self.body, self.logger
            ).template_args()
            try:
                helmbundles_body[s] = layers.merge_all_layers(
                    s,
                    self.body,
                    self.body["metadata"],
                    self.mspec,
                    self.logger,
                    **service_template_args,
                )
            except Exception as e:
                raise kopf.PermanentError(
                    f"Error while rendering HelmBundle for {self.service} "
                    f"service: {e}"
                )

        template_args["helmbundles_body"] = helmbundles_body
        return template_args


class Masakari(OpenStackService):
    service = "instance-ha"
    openstack_chart = "masakari"


registry = Service.registry
