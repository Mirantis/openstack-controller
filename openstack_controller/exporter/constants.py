from enum import IntEnum


class ServiceState(IntEnum):
    up = 1
    down = 0


class ServiceStatus(IntEnum):
    enabled = 1
    disabled = 0


class LoadbalancerStatus(IntEnum):
    ONLINE = 0
    DRAINING = 1
    OFFLINE = 2
    DEGRADED = 3
    ERROR = 4
    NO_MONITOR = 5


class LoadbalancerProvisioningStatus(IntEnum):
    ACTIVE = 0
    DELETED = 1
    ERROR = 2
    PENDING_CREATE = 3
    PENDING_UPDATE = 4
    PENDING_DELETE = 5


"Binary giga unit"
Gi = 1024**3
