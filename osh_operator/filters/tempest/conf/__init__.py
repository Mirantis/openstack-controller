from osh_operator.filters.tempest.conf import auth

from osh_operator.filters.tempest.conf import baremetal
from osh_operator.filters.tempest.conf import baremetal_feature_enabled
from osh_operator.filters.tempest.conf import compute
from osh_operator.filters.tempest.conf import compute_feature_enabled
from osh_operator.filters.tempest.conf import dashboard
from osh_operator.filters.tempest.conf import debug
from osh_operator.filters.tempest.conf import default
from osh_operator.filters.tempest.conf import dns
from osh_operator.filters.tempest.conf import dns_feature_enabled
from osh_operator.filters.tempest.conf import heat_plugin
from osh_operator.filters.tempest.conf import identity
from osh_operator.filters.tempest.conf import identity_feature_enabled
from osh_operator.filters.tempest.conf import image
from osh_operator.filters.tempest.conf import image_feature_enabled
from osh_operator.filters.tempest.conf import network
from osh_operator.filters.tempest.conf import network_feature_enabled
from osh_operator.filters.tempest.conf import object_storage
from osh_operator.filters.tempest.conf import object_storage_feature_enabled
from osh_operator.filters.tempest.conf import orchestration
from osh_operator.filters.tempest.conf import oslo_concurrency
from osh_operator.filters.tempest.conf import patrole_plugin
from osh_operator.filters.tempest.conf import scenario
from osh_operator.filters.tempest.conf import service_clients
from osh_operator.filters.tempest.conf import service_available
from osh_operator.filters.tempest.conf import share
from osh_operator.filters.tempest.conf import telemetry
from osh_operator.filters.tempest.conf import tungsten_plugin
from osh_operator.filters.tempest.conf import validation
from osh_operator.filters.tempest.conf import volume
from osh_operator.filters.tempest.conf import volume_feature_enabled

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
    heat_plugin.HeatPlugin,
    identity.Identity,
    identity_feature_enabled.IdentityFeatureEnabled,
    image.Image,
    image_feature_enabled.ImageFeatureEnabled,
    network.Network,
    network_feature_enabled.NetworkFeatureEnabled,
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
