from collections import deque
import kopf
import os
import subprocess
import time

from openstack_controller import settings
from openstack_controller import utils


LOG = utils.get_logger(__name__)

RECV_QUEUE_LEN = 3
RECV_QUEUE = deque(RECV_QUEUE_LEN * [0], RECV_QUEUE_LEN)


@kopf.on.probe(id="recv_q")
def check_recv_queue(**kwargs):
    """ Check if tcp recieve queue is not processing.

    When tcp queue is not equal to 0 and growing during last 3 times
    or not changing raise error.

    """
    cmd = ["netstat", "-plan", "--tcp"]
    cmd_res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    pid = os.getpid()
    LOG.debug(f"Checking Rec-Q for pid: {pid}")
    global RECV_QUEUE
    recv_q_max = 0
    for line in cmd_res.stdout.splitlines():
        out = line.strip().split()
        # proto, recvQ, sendQ, local, remote, state, pid/name
        if out[0] == "tcp" and out[6].startswith(f"{pid}/"):
            recv_q = int(out[1])
            recv_q_max = max(recv_q_max, recv_q)

    LOG.debug(f"The Rec-Q for pid: {pid} is: {RECV_QUEUE}")

    RECV_QUEUE.append(recv_q_max)

    if recv_q_max == 0 or set(list(RECV_QUEUE)[:-1]) == {0}:
        return list(RECV_QUEUE)

    # In case the queue is growing or not changing
    if list(RECV_QUEUE) == sorted(RECV_QUEUE):
        LOG.debug(f"The Rec-Q for pid: {pid} is: {recv_q}")
        raise ValueError(
            f"The Rec-Q for {pid} is growing or not changing {RECV_QUEUE}"
        )
    return list(RECV_QUEUE)


@kopf.on.probe(id="delay")
def check_heartbeat(**kwargs):
    delay = None
    if settings.OSCTL_HEARTBEAT_INTERVAL:
        delay = time.time() - settings.HEARTBEAT
        LOG.debug(f"Current heartbeat delay {delay}")
        if delay > settings.OSCTL_HEARTBEAT_MAX_DELAY:
            raise ValueError("Heartbeat delay is too large")
    return delay


@kopf.on.probe(id="tasks")
def check_number_of_tasks(**kwargs):
    tasks = settings.CURRENT_NUMBER_OF_TASKS
    if tasks > settings.OSCTL_MAX_TASKS:
        raise ValueError("Too many tasks")
    return tasks
