from openstack_controller.filters.tempest.conf import auth

from openstack_controller.filters.tempest.conf import baremetal
from openstack_controller.filters.tempest.conf import baremetal_feature_enabled
from openstack_controller.filters.tempest.conf import compute
from openstack_controller.filters.tempest.conf import compute_feature_enabled
from openstack_controller.filters.tempest.conf import dashboard
from openstack_controller.filters.tempest.conf import debug
from openstack_controller.filters.tempest.conf import default
from openstack_controller.filters.tempest.conf import dns
from openstack_controller.filters.tempest.conf import dns_feature_enabled
from openstack_controller.filters.tempest.conf import (
    ephemeral_storage_encryption,
)
from openstack_controller.filters.tempest.conf import heat_plugin
from openstack_controller.filters.tempest.conf import identity
from openstack_controller.filters.tempest.conf import identity_feature_enabled
from openstack_controller.filters.tempest.conf import image
from openstack_controller.filters.tempest.conf import (
    image_signature_verification,
)
from openstack_controller.filters.tempest.conf import image_feature_enabled
from openstack_controller.filters.tempest.conf import load_balancer
from openstack_controller.filters.tempest.conf import (
    loadbalancer_feature_enabled,
)
from openstack_controller.filters.tempest.conf import network
from openstack_controller.filters.tempest.conf import network_feature_enabled
from openstack_controller.filters.tempest.conf import neutron_plugin_options
from openstack_controller.filters.tempest.conf import object_storage
from openstack_controller.filters.tempest.conf import (
    object_storage_feature_enabled,
)
from openstack_controller.filters.tempest.conf import orchestration
from openstack_controller.filters.tempest.conf import oslo_concurrency
from openstack_controller.filters.tempest.conf import patrole_plugin
from openstack_controller.filters.tempest.conf import scenario
from openstack_controller.filters.tempest.conf import service_clients
from openstack_controller.filters.tempest.conf import service_available
from openstack_controller.filters.tempest.conf import share
from openstack_controller.filters.tempest.conf import telemetry
from openstack_controller.filters.tempest.conf import tungsten_plugin
from openstack_controller.filters.tempest.conf import validation
from openstack_controller.filters.tempest.conf import volume
from openstack_controller.filters.tempest.conf import volume_feature_enabled

SECTIONS = [
    auth.Auth,
    baremetal.Baremetal,
    baremetal_feature_enabled.BaremetalFeatureEnabled,
    compute.Compute,
    compute_feature_enabled.ComputeFeatureEnabled,
    dashboard.Dashboard,
    debug.Debug,
    default.Default,
    dns.Dns,
    dns_feature_enabled.DnsFeatureEnabled,
    ephemeral_storage_encryption.EphemeralStorageEncryption,
    heat_plugin.HeatPlugin,
    identity.Identity,
    identity_feature_enabled.IdentityFeatureEnabled,
    image.Image,
    image_feature_enabled.ImageFeatureEnabled,
    image_signature_verification.ImageSignatureVerification,
    load_balancer.LoadBalancer,
    loadbalancer_feature_enabled.LoadBalancerFeatureEnabled,
    network.Network,
    network_feature_enabled.NetworkFeatureEnabled,
    neutron_plugin_options.NeutronPluginOptions,
    object_storage.ObjectStorage,
    object_storage_feature_enabled.ObjectStorageFeatureEnabled,
    orchestration.Orchestration,
    oslo_concurrency.OsloConcurrency,
    patrole_plugin.PatrolePlugin,
    scenario.Scenario,
    service_clients.ServiceClients,
    service_available.ServiceAvailable,
    share.Share,
    telemetry.Telemetry,
    tungsten_plugin.TungstenPlugin,
    validation.Validation,
    volume.Volume,
    volume_feature_enabled.VolumeFeatureEnabled,
]
