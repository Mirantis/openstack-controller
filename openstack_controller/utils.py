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
import functools
import logging
import os
import threading
from typing import Dict, List

from openstack_controller import settings
from kopf.engines.posting import event_queue_var


def get_in(d: Dict, keys: List, default=None):
    """Returns the value in a nested dict, where keys is a list of keys.

    >>> get_in({"a": {"b": 1}}, ["a", "b"])
    1
    >>> get_in({"a": [0, 1, 2]}, ["a", 1])
    1
    >>> get_in({"a": {"b": 1}}, ["a", "x"], "not found")
    'not found'

    """
    if not keys:
        return d
    try:
        return get_in(d[keys[0]], keys[1:], default)
    except (KeyError, IndexError):
        return default


def get_logger(name: str) -> logging.Logger:
    verbose = os.getenv("KOPF_RUN_VERBOSE")
    debug = os.getenv("KOPF_RUN_DEBUG")
    quiet = os.getenv("KOPF_RUN_QUIET")

    log_level = "DEBUG" if debug or verbose else "WARNING" if quiet else "INFO"
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    return logger


def to_base64(value: str) -> str:
    return base64.encodebytes(value.encode("ascii")).decode("ascii")


def from_base64(value: str) -> str:
    return base64.decodebytes(value.encode("ascii")).decode("ascii")


def collect_handler_metrics(func):

    handler_latency = settings.METRICS["handler_latency"].labels(func.__name__)
    handler_errors = settings.METRICS["handler_errors"].labels(func.__name__)
    handler_last = settings.METRICS["handler_last"].labels(func.__name__)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with handler_errors.count_exceptions():
            with handler_latency.time():
                r = await func(*args, **kwargs)
        handler_last.set_to_current_time()
        try:
            qsize = event_queue_var.get().qsize()
        except LookupError:
            qsize = -1
        settings.METRICS["queue"].set(qsize)
        settings.METRICS["threads"].set(threading.active_count())
        return r

    return wrapper


def divide_into_groups_of(group_len, collection):
    groups = []
    for i in range(len(collection) // group_len):
        groups.append(collection[i * group_len : i * group_len + group_len])
    if len(collection) % group_len:
        groups.append(collection[-(len(collection) % group_len) :])
    return groups


async def async_retry(function, *args, **kwargs):
    result = None
    while not result:
        result = function(*args, **kwargs)
        if result:
            return result
        await asyncio.sleep(10)
