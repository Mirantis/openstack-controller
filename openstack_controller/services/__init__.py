import kopf
from mcp_k8s_lib import utils

from openstack_controller import constants
from openstack_controller import layers
from openstack_controller import kube
from openstack_controller import secrets
from .base import Service, OpenStackService, OpenStackServiceWithCeph


LOG = utils.get_logger(__name__)

# INFRA SERVICES


class Ingress(Service):
    service = "ingress"

    @property
    def health_groups(self):
        return ["ingress"]


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

    def template_args(self, spec):
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
                }
            }
        }
    }

    def template_args(self, spec):
        credentials = {}
        admin_creds = self._get_admin_creds()
        services = set(spec["features"]["services"]) - set(["tempest"])
        for s in services:
            if s not in constants.OS_SERVICES_MAP:
                continue
            # TODO: 'use get or wait' approach for generated credential here
            secret = secrets.OpenStackServiceSecret(self.namespace, s)
            credentials[s] = secret.ensure()

        return {
            "services": services,
            "credentials": credentials,
            "admin_creds": admin_creds,
        }


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
            }
        },
        "rabbitmq": {
            "Job": {
                "openstack-cinder-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                }
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
                }
            }
        },
    }

    def template_args(self, spec):
        t_args = super().template_args(spec)
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
            }
        },
        "rabbitmq": {
            "Job": {
                "openstack-glance-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                }
            }
        },
    }


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
                },
                "heat-trustee-ks-user": {
                    "images": ["ks_user"],
                    "manifest": "job_ks_user_trustee",
                },
                "heat-trusts": {"images": ["ks_user"], "manifest": ""},
            }
        },
        "rabbitmq": {
            "Job": {
                "openstack-heat-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                }
            }
        },
    }


class Horizon(OpenStackService):
    service = "dashboard"
    openstack_chart = "horizon"

    @property
    def _child_generic_objects(self):
        return {"horizon": {"job_db_init", "job_db_sync", "job_db_drop"}}


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
                },
                "keystone-fernet-setup": {
                    "images": ["keystone_fernet_setup"],
                    "manifest": "job_fernet_setup",
                },
                "keystone-credential-setup": {
                    "images": ["keystone_credential_setup"],
                    "manifest": "job_credential_cleanup",
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
                }
            }
        },
    }

    def template_args(self, spec):
        t_args = super().template_args(spec)
        keycloak_enabled = (
            spec.get("features", {})
            .get("keystone", {})
            .get("keycloak", {})
            .get("enabled", False)
        )

        if not keycloak_enabled:
            return t_args

        keycloak_salt = secrets.KeycloakSecret(self.namespace)
        t_args["oidc_crypto_passphrase"] = keycloak_salt.ensure().passphrase

        return t_args

    @layers.kopf_exception
    async def _upgrade(self, event, **kwargs):
        await self.wait_service_healthy()

        LOG.info(f"Upgrading {self.service} started")
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
    _required_accounts = {"compute": ["nova"], "dns": ["designate"]}

    @property
    def health_groups(self):
        return [self.openstack_chart, "openvswitch"]

    _child_objects = {
        "rabbitmq": {
            "Job": {
                "openstack-neutron-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                }
            }
        }
    }


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
        r_accounts = {"networking": ["neutron"]}  # ironic
        if self.openstack_version not in [
            "queens",
            "rocky",
        ]:
            r_accounts["placement"] = ["placement"]
        return r_accounts

    @property
    def _child_objects(self):
        nova_jobs = {
            "nova-cell-setup": {
                "images": ["nova_cell_setup", "nova_cell_setup_init"],
                "manifest": "job_cell_setup",
            },
        }
        if self.openstack_version in [
            "queens",
            "rocky",
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
        return {
            "nova": {"Job": nova_jobs,},
            "rabbitmq": {
                "Job": {
                    "openstack-nova-rabbitmq-cluster-wait": {
                        "images": ["rabbitmq_scripted_test"],
                        "manifest": "job_cluster_wait",
                    }
                }
            },
        }

    def template_args(self, spec):
        t_args = super().template_args(spec)
        ssh_secret = secrets.SSHSecret(self.namespace, "nova")
        t_args["ssh_credentials"] = ssh_secret.ensure()
        return t_args


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


class Octavia(OpenStackService):
    service = "load-balancer"
    openstack_chart = "octavia"
    _child_objects = {
        "octavia": {
            "Job": {
                "octavia-create-resources": {
                    "images": ["create_resources"],
                    "manifest": "job_create_resources",
                }
            }
        },
        "rabbitmq": {
            "Job": {
                "openstack-octavia-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                }
            }
        },
    }

    def template_args(self, spec):
        t_args = super().template_args(spec)
        cert_secret = secrets.SignedCertificateSecret(
            self.namespace, "octavia"
        )
        cert_secret.ensure()
        ssh_secret = secrets.SSHSecret(self.namespace, self.service)
        t_args["ssh_credentials"] = ssh_secret.ensure()
        return t_args

    async def cleanup_immutable_resources(self, new_obj, rendered_spec):
        await super().cleanup_immutable_resources(new_obj, rendered_spec)

        old_obj = kube.resource(rendered_spec)
        old_obj.reload()

        obj_name = "octavia-create-resources"
        resource = self.get_child_object("Job", obj_name)

        for old_release in old_obj.obj["spec"]["releases"]:
            if old_release["chart"].endswith(f"/{self.openstack_chart}"):
                for new_release in new_obj.obj["spec"]["releases"]:
                    if new_release["chart"].endswith(
                        f"/{self.openstack_chart}"
                    ):
                        old_image = old_release["values"]["octavia"][
                            "settings"
                        ].get("amphora_image_url")
                        new_image = new_release["values"]["octavia"][
                            "settings"
                        ]["amphora_image_url"]
                        if old_image is None or old_image != new_image:
                            LOG.info(
                                f"Removing the following jobs: [{obj_name}]"
                            )
                            await resource.purge()


class RadosGateWay(Service):
    service = "object-storage"


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

    def template_args(self, spec):
        # TODO: add wait for generated credential here
        admin_creds = self._get_admin_creds()
        secret = secrets.OpenStackServiceSecret(self.namespace, self.service)
        credentials = secret.ensure()
        helmbundles_body = {}
        for s in set(spec["features"]["services"]) - {"tempest"}:
            template_args = Service.registry[s](
                self.body, self.logger
            ).template_args(spec)
            try:
                helmbundles_body[s] = layers.merge_all_layers(
                    s,
                    self.body,
                    self.body["metadata"],
                    spec,
                    self.logger,
                    **template_args,
                )
            except Exception as e:
                raise kopf.PermanentError(
                    f"Error while rendering HelmBundle for {self.service} "
                    f"service: {e}"
                )
        return {
            "helmbundles_body": helmbundles_body,
            "admin_creds": admin_creds,
            "credentials": credentials,
        }


registry = Service.registry
