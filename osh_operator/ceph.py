"""
This file contains api shared with OS Controller
Copy paste from mcp/mcp-k8s-lib.git/mcp_k8s_lib/ceph_api.py
"""
from __future__ import annotations

import base64
import struct
from dataclasses import dataclass
from enum import Enum, auto
from ipaddress import IPv4Address
from typing import Tuple, Iterable, Iterator, Callable, Dict, List, Any


OPENSTACK_KEYS_SECRET = "openstack-ceph-keys"
OPENSTACK_SECRET_NAMESPACE = "ceph-lcm-mirantis"
CEPH_OPENSTACK_TARGET_SECRET = "rook-ceph-admin-keyring"
CEPH_OPENSTACK_TARGET_CONFIGMAP = "rook-ceph-config"


class OSUser(Enum):
    compute = auto()
    cinder = auto()
    glance = auto()


@dataclass
class OSServiceCreds:
    os_user: OSUser
    key: str
    pools: List[str]


@dataclass
class OSCephParams:
    admin_user = "client.admin"
    admin_key: str
    mon_endpoints: List[Tuple[IPv4Address, int]]
    services: List[OSServiceCreds]


class CephStatus:
    waiting = "waiting"
    created = "created"


def _os_ceph_params_to_secret(params: OSCephParams) -> Dict[str, str]:
    data = {
        params.admin_user: params.admin_key,
        "mon_endpoints": base64.encodebytes(
            _pack_ips(params.mon_endpoints)
        ).decode("ascii"),
    }

    for service in params.services:
        vl = ";".join([service.key] + service.pools)
        data[service.os_user.name] = base64.encodebytes(
            vl.encode("ascii")
        ).decode("ascii")
    return data


def _os_ceph_params_from_secret(secret: Dict[str, str]) -> OSCephParams:
    local_secret = secret.copy()
    admin_key = local_secret.pop(OSCephParams.admin_user)
    mon_endpoints = list(_unpack_ips(local_secret.pop("mon_endpoints")))

    services: List[OSServiceCreds] = []
    for os_user, val in local_secret.items():
        key, *pools = val.split(";")
        services.append(
            OSServiceCreds(os_user=OSUser[os_user], key=key, pools=pools)
        )
    return OSCephParams(
        admin_key=admin_key, mon_endpoints=mon_endpoints, services=services
    )


_IP_SIZE = 4
_PORT_PACK_FORMAT = ">H"
_PORT_SIZE = struct.calcsize(_PORT_PACK_FORMAT)
_BLOCK_SIZE = _IP_SIZE + _PORT_SIZE


def _pack_ips(ips_and_ports: Iterable[Tuple[IPv4Address, int]]) -> bytes:
    res = []
    for ip, port in ips_and_ports:
        assert len(ip.packed) == _IP_SIZE
        res.append(ip.packed + struct.pack(_PORT_PACK_FORMAT, port))
    return b"".join(res)


def _unpack_ips(data: bytes) -> Iterator[Tuple[IPv4Address, int]]:
    assert len(data) % _BLOCK_SIZE == 0

    for cnt in range(len(data) // _BLOCK_SIZE):
        block = data[cnt * _BLOCK_SIZE : (cnt + 1) * _BLOCK_SIZE]
        yield IPv4Address(block[:_IP_SIZE]), struct.unpack(
            ">H", block[_IP_SIZE:]
        )[0]


def get_os_ceph_params(
    read_secret: Callable[[str, str], Dict[str, str]]
) -> OSCephParams:
    return _os_ceph_params_from_secret(
        read_secret(OPENSTACK_SECRET_NAMESPACE, OPENSTACK_KEYS_SECRET)
    )


def set_os_ceph_params(
    os_params: OSCephParams,
    save_secret: Callable[[str, str, Dict[str, str]], Any],
) -> None:
    save_secret(
        OPENSTACK_SECRET_NAMESPACE,
        OPENSTACK_KEYS_SECRET,
        _os_ceph_params_to_secret(os_params),
    )
