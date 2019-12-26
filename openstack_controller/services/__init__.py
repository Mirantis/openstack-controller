from dataclasses import asdict

import kopf

from openstack_controller import layers
from openstack_controller import openstack
from openstack_controller import secrets
from .base import Service, OpenStackService

# INFRA SERVICES


class Ingress(Service):
    service = "ingress"


class MariaDB(Service):
    service = "database"
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
        admin_creds = openstack.get_admin_credentials(self.namespace)
        galera_creds = openstack.get_or_create_galera_credentials(
            self.namespace
        )
        return {"admin_creds": admin_creds, "galera_creds": galera_creds}


class Memcached(Service):
    service = "memcached"


class RabbitMQ(Service):
    service = "messaging"
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
        admin_creds = openstack.get_admin_credentials(self.namespace)
        services = set(spec["features"]["services"]) - set(["tempest"])
        for s in services:
            if s not in openstack.OS_SERVICES_MAP:
                continue
            # TODO: 'use get or wait' approach for generated credential here
            credentials[s] = openstack.get_or_create_os_credentials(
                s, self.namespace
            )

        return {
            "services": services,
            "credentials": credentials,
            "admin_creds": admin_creds,
        }


# OPENSTACK SERVICES


class Barbican(OpenStackService):
    service = "key-manager"
    openstack_chart = "barbican"
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


class Cinder(OpenStackService):
    ceph_required = True
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
        "rabbitmq": {
            "Job": {
                "openstack-designate-rabbitmq-cluster-wait": {
                    "images": ["rabbitmq_scripted_test"],
                    "manifest": "job_cluster_wait",
                }
            }
        }
    }

    def template_args(self, spec):
        t_args = super().template_args(spec)
        credentials = openstack.get_or_create_os_credentials(
            self.backend_service, self.namespace
        )
        t_args[self.backend_service] = credentials

        return t_args


class Glance(OpenStackService):
    ceph_required = True
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
    keycloak_secret = "oidc-crypto-passphrase"
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

        keycloak_salt = secrets.get_or_create_keycloak_salt(
            self.namespace, self.keycloak_secret
        )
        t_args[self.keycloak_secret] = keycloak_salt

        return t_args


class Neutron(OpenStackService):
    service = "networking"
    openstack_chart = "neutron"
    _required_accounts = {"compute": ["nova"], "dns": ["designate"]}

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


class Nova(OpenStackService):
    service = "compute"
    ceph_required = True
    openstack_chart = "nova"

    @property
    def _service_accounts(self):
        s_accounts = []
        if self.osdpl.obj["spec"]["openstack_version"] in [
            "queens",
            "rocky",
            "stein",
        ]:
            s_accounts.append("placement")
        return s_accounts

    @property
    def _required_accounts(self):
        r_accounts = {"networking": ["neutron"]}  # ironic
        if self.osdpl.obj["spec"]["openstack_version"] not in [
            "queens",
            "rocky",
            "stein",
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
        if self.osdpl.obj["spec"]["openstack_version"] in [
            "queens",
            "rocky",
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
        t_args["ssh_credentials"] = asdict(
            openstack.get_or_create_ssh_credentials("nova", self.namespace)
        )
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
        openstack.get_or_create_certs("octavia-certs", self.namespace)
        t_args["ssh_credentials"] = asdict(
            openstack.get_or_create_ssh_credentials(
                self.service, self.namespace
            )
        )
        return t_args


class RadosGateWay(Service):
    service = "object-storage"


class Tempest(Service):
    service = "tempest"

    def template_args(self, spec):
        # TODO: add wait for generated credential here
        admin_creds = openstack.get_admin_credentials(self.namespace)
        credentials = openstack.get_or_create_os_credentials(
            self.service, self.namespace
        )
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
                raise kopf.HandlerFatalError(
                    f"Error while rendering HelmBundle for {self.service} "
                    f"service: {e}"
                )
        return {
            "helmbundles_body": helmbundles_body,
            "admin_creds": admin_creds,
            "credentials": credentials,
        }


registry = Service.registry
