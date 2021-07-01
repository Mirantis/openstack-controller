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
import os
import time
import logging.config

import json
import kopf
from kopf.engines.posting import event_queue_var
from prometheus_client import start_http_server, Gauge, Counter, Summary

from openstack_controller.utils import merger


HEARTBEAT = time.time()
CURRENT_NUMBER_OF_TASKS = -1

TRUE_STRINGS = {"1", "t", "true", "on", "y", "yes"}
FALSE_STRINGS = {"0", "f", "false", "off", "n", "no"}


def bool_from_env(env_name, default):
    """Convert env variable into boolean
    :param env_name: the name of environment variable
    :param default: the default value to return
    :returns True: when value of env is in TRUE_STRINGS
    :returns False: when value of env is in FALSE_STRINGS
    :raise kopf.PermanentError: when value not in TRUE_STRINGS or FALSE_STRINGS
    """

    data = os.environ.get(env_name)

    if data is None:
        return default

    lowered = data.strip().lower()

    if lowered in TRUE_STRINGS:
        return True
    elif lowered in FALSE_STRINGS:
        return False

    raise kopf.PermanentError(f"Failed to convert {data} into boolean.")


def json_from_env(env_name, default):
    """Load a json string from an env variable

    :param env_name: the name of environment variable
    :param default: the default value to return
    :returns True: when value of env is in TRUE_STRINGS
    :returns False: when value of env is in FALSE_STRINGS
    :raise kopf.PermanentError: when value not in TRUE_STRINGS or FALSE_STRINGS

    """
    data = os.environ.get(env_name)

    if data is None:
        return default

    return json.loads(data)


# The number of seconds to wait for all component from application becomes ready
OSCTL_WAIT_APPLICATION_READY_TIMEOUT = int(
    os.environ.get("OSCTL_WAIT_APPLICATION_READY_TIMEOUT", 1200)
)

# The number of seconds to sleep between checking application ready attempts
OSCTL_WAIT_APPLICATION_READY_DELAY = int(
    os.environ.get("OSCTL_WAIT_APPLICATION_READY_DELAY", 10)
)

# The number of seconds to wait for values set in manifest are propagated to child objects.
OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_ENABLE_TIMEOUT", 600)
)

# The number of seconds between attempts to check that values were applied.
OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_ENABLE_DELAY", 10)
)

# The number of seconds to wait for values are removed from manifest and propagated to child objects.
OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_DISABLE_TIMEOUT", 600)
)

# The number of seconds between attempts to check that values were removed from release.
OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_DISABLE_DELAY", 10)
)

# The number of seconds to wait for kubernetes object removal
OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_PURGE_TIMEOUT", 600)
)

# The number of seconds between attempts to check that kubernetes object is removed
OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY = int(
    os.environ.get("OSCTL_HELMBUNLE_MANIFEST_PURGE_DELAY", 10)
)

# The number of seconds to pause for helmbundle changes
OSCTL_HELMBUNDLE_APPLY_DELAY = int(
    os.environ.get("OSCTL_HELMBUNDLE_APPLY_DELAY", 10)
)

# The amount of time to wit for flapping node
OSCTL_NODE_NOT_READY_FLAPPING_TIMEOUT = int(
    os.environ.get("OSCTL_NODE_NOT_READY_FLAPPING_TIMEOUT", 120)
)

# The name of openstack deployment namespace
OSCTL_OS_DEPLOYMENT_NAMESPACE = os.environ.get(
    "OSCTL_OS_DEPLOYMENT_NAMESPACE", "openstack"
)

# The name of openstack deployment namespace
OSCTL_CEPH_SHARED_NAMESPACE = os.environ.get(
    "OSCTL_CEPH_SHARED_NAMESPACE", "openstack-ceph-shared"
)

# TODO(mkarpin): move openstack related settings to separate file
# as settings.py is imported inside kube.py
# Url for openstack binaries/helm charts
OSCTL_BINARY_BASE_URL = os.environ.get("OSCTL_BINARY_BASE_URL", "")
# Url for openstack docker images
OSCTL_IMAGES_BASE_URL = os.environ.get("OSCTL_IMAGES_BASE_URL", "")

# The name of secret with BGP information
OSCTL_BGPVPN_NEIGHBOR_INFO_SECRET_NAME = os.environ.get(
    "OSCTL_BGPVPN_BGP_NEIGHBOR_INFO_SECRET_NAME", "frr-bgp-neighbors"
)

# The number of retries while waiting a resouce deleted
OSCTL_RESOURCE_DELETED_WAIT_RETRIES = int(
    os.environ.get("OSCTL_RESOURCE_DELETED_WAIT_RETRIES", 120)
)

# The number of seconds to sleep while waiting a resouce deleted
OSCTL_RESOURCE_DELETED_WAIT_TIMEOUT = int(
    os.environ.get("OSCTL_RESOURCE_DELETED_WAIT_TIMEOUT", 1)
)

OSCTL_REDIS_NAMESPACE = os.environ.get(
    "OSCTL_REDIS_NAMESPACE", "openstack-redis"
)

OSCTL_HEARTBEAT_INTERVAL = int(os.environ.get("OSCTL_HEARTBEAT_INTERVAL", 300))

OSCTL_HEARTBEAT_MAX_DELAY = int(
    os.environ.get("OSCTL_HEARTBEAT_MAX_DELAY", OSCTL_HEARTBEAT_INTERVAL * 3)
)

OSCTL_BATCH_HEATH_UPDATER_PERIOD = int(
    os.environ.get("OSCTL_BATCH_HEATH_UPDATER_PERIOD", 60)
)

OSCTL_PYKUBE_HTTP_REQUEST_TIMEOUT = float(
    os.environ.get("OSCTL_PYKUBE_HTTP_REQUEST_TIMEOUT", 60)
)

OSCTL_MAX_TASKS = int(os.environ.get("OSCTL_MAX_TASKS", 150))

# The port number for /metrics endpoint. If the value is less or equal to zero
# metrics http server will not start.
OSCTL_METRICS_PORT = int(os.environ.get("OSCTL_METRICS_PORT", -1))

METRICS = {
    "queue": Gauge(
        "openstack_controller_task_queue_size", "The size of task queue."
    ),
    "threads": Gauge("openstack_controller_threads", "The number of threads."),
    "handler_latency": Summary(
        "openstack_controller_handler_latency_seconds",
        "Time for a handler.",
        labelnames=["handler"],
    ),
    "handler_errors": Counter(
        "openstack_controller_handler_errors_total",
        "The nubmer of errors for a handler.",
        labelnames=["handler"],
    ),
    "handler_last": Gauge(
        "openstack_controller_handler_last_time_seconds",
        "The last time a k8s event was served by openstack-controller specific handler.",
        labelnames=["handler"],
    ),
}

OSCTL_HEARTBEAT_PEERING_OBJECT_NAME = os.environ.get(
    "OSCTL_HEARTBEAT_PEERING_OBJECT_NAME", "openstack-controller.osdpl"
)

if OSCTL_HEARTBEAT_INTERVAL:

    @kopf.timer(
        "zalando.org",
        "v1",
        "kopfpeerings",
        interval=OSCTL_HEARTBEAT_INTERVAL,
        when=lambda name, **_: OSCTL_HEARTBEAT_PEERING_OBJECT_NAME == name,
    )
    async def heartbeat(spec, **kwargs):
        global HEARTBEAT
        global CURRENT_NUMBER_OF_TASKS
        HEARTBEAT = time.time()
        CURRENT_NUMBER_OF_TASKS = event_queue_var.get().qsize()


# The interval for periodic check of helm releases
OSCTL_HEALTH_INTERVAL = int(os.environ.get("OSCTL_HEALTH_INTERVAL", 60))

# Number of instances to migrate off node concurrently
OSCTL_MIGRATE_CONCURRENCY = int(os.environ.get("OSCTL_MIGRATE_CONCURRENCY", 5))

# Whether to perform evacuation if compute node is down, or just error out
OSCTL_ALLOW_EVACUATION = bool_from_env("OSCTL_ALLOW_EVACUATION", False)

# A dict of OpenStack node labels in json format.
# For example `OSCTL_OPENSTACK_NODE_LABELS={"openstack-compute-node":"enabled","openstack-control-plane":"enabled"}`
# If a node has one of specified labels with the matching value an appropriate NodeWorkloadLock object will be created.
OSCTL_OPENSTACK_NODE_LABELS = json_from_env(
    "OSCTL_OPENSTACK_NODE_LABELS", {"openstack-compute-node": "enabled"}
)
try:
    for x, y in OSCTL_OPENSTACK_NODE_LABELS.items():
        pass
except Exception:
    raise kopf.PermanentError(
        f"OSCTL_OPENSTACK_NODE_LABELS invalid format, should be a dict with node labels and values"
    )

# The dict defining proxy settings
OSCTL_PROXY_DATA = json_from_env("OSCTL_PROXY_DATA", {"enabled": False})
OSCTL_PROXY_SECRET_NAMESPACE = os.environ.get(
    "OSCTL_PROXY_SECRET_NAMESPACE", "osh-system"
)

# The dict defining IAM data {"client": "os", "enabled": True, "oidcCASecret": "oidc-cert", url: "https://1.2.3.4"}
OSDPL_IAM_DATA = json_from_env("OSDPL_IAM_DATA", {"enabled": False})

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
    },
    "loggers": {
        "kopf.activities.probe": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["default"],
        "level": "INFO",
    },
}

OSCTL_LOGGING_CONF = json_from_env("OSCTL_LOGGING_CONF", {})
merger.merge(LOGGING_CONFIG, OSCTL_LOGGING_CONF)

logging.config.dictConfig(LOGGING_CONFIG)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.watching.connect_timeout = 1 * 60
    # NOTE(vsaienko): The watching.server_timeout is used to set timeoutSeconds
    # for kubernetes watching request.
    # Timeout for the list/watch call. This limits the duration of the call,
    # regardless of any activity or inactivity.
    # IMPORTANT: this timeout have to be less than aiohttp client.timeout
    settings.watching.server_timeout = os.environ.get(
        "KOPF_WATCH_STREAM_TIMEOUT", 1 * 300
    )
    # Defines total timeout for aiohttp watching session.
    settings.watching.client_timeout = 1 * 600
    if OSCTL_METRICS_PORT > 0:
        start_http_server(OSCTL_METRICS_PORT)
