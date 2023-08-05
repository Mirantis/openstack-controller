from enum import IntEnum


class ServiceState(IntEnum):
    up = 1
    down = 0


class ServiceStatus(IntEnum):
    enabled = 1
    disabled = 0


"Binary giga unit"
Gi = 1024**3
