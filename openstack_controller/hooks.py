import asyncio

import kopf
import pykube

from openstack_controller import kube

from mcp_k8s_lib import utils

LOG = utils.get_logger(__name__)


def new_node_added(**kwargs):
    if (
        kwargs["new"]["desiredNumberScheduled"]
        <= kwargs["OK_desiredNumberScheduled"]
    ):
        LOG.info("The number of computes was not increased. Skipping hook...")
        return False
    return True


async def run_nova_cell_setup(osdpl, name, namespace, meta, **kwargs):
    LOG.info("Start nova daemonset created hook")
    if not new_node_added(**kwargs):
        return
    cronjob = kube.find(pykube.CronJob, "nova-cell-setup", namespace)
    job = {
        "metadata": {
            "name": "nova-cell-setup-online",
            "namespace": namespace,
            "annotations": cronjob.obj["metadata"]["annotations"],
            "labels": cronjob.obj["spec"]["jobTemplate"]["metadata"]["labels"],
        },
        "spec": cronjob.obj["spec"]["jobTemplate"]["spec"],
    }
    job["spec"]["backoffLimit"] = 10
    job["spec"]["ttlSecondsAfterFinished"] = 60
    job["spec"]["template"]["spec"]["restartPolicy"] = "OnFailure"
    kopf.adopt(job, osdpl.obj)
    kube_job = kube.Job(kube.api, job)
    try:
        kube_job.create()
    except pykube.exceptions.HTTPError as e:
        LOG.info(f"Cannot create nova-cell-setup-job, error: {e}")
        job_already_exists = e.code == 409
        if not job_already_exists:
            raise
        if kube_job.ready:
            kube_job.delete()
            await asyncio.sleep(1)
            await run_nova_cell_setup(osdpl, name, namespace, meta, **kwargs)


async def run_octavia_create_resources(osdpl, name, namespace, meta, **kwargs):
    LOG.info("Start rerun_octavia_create_resources_job hook")
    if not new_node_added(**kwargs):
        return
    try:
        job = kube.find(kube.Job, "octavia-create-resources", namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        # TODO(avolkov): create job manually?
        LOG.warning("Original octavia_create_resources job is not found")
        return
    if not job.ready:
        LOG.warning("Original octavia_create_resources job is not ready")
        return
    await job.rerun()
