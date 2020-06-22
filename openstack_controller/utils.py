import base64
import logging
import os
from typing import Dict, List


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
