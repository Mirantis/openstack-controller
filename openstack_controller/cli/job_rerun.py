#!/usr/bin/env python3
import argparse
import sys
import time

import pykube


def parse_args():
    parser = argparse.ArgumentParser(
        prog="osctl-job-rerun", description="Delete and re-create a job"
    )
    parser.add_argument("name", help=("Job name"))
    parser.add_argument("namespace", help=("Job's namespace"))
    return parser.parse_args()


def purge_job_meta(job):
    # cleanup the object of runtime stuff
    job.obj.pop("status", None)
    job.obj["metadata"].pop("creationTimestamp", None)
    job.obj["metadata"].pop("resourceVersion", None)
    job.obj["metadata"].pop("selfLink", None)
    job.obj["metadata"].pop("uid", None)
    job.obj["metadata"]["labels"].pop("controller-uid", None)
    job.obj["spec"]["template"]["metadata"].pop("creationTimestamp", None)
    job.obj["spec"]["template"]["metadata"]["labels"].pop(
        "controller-uid", None
    )
    job.obj["spec"].pop("selector", None)


def main():
    args = parse_args()
    api = pykube.HTTPClient(pykube.KubeConfig.from_env())
    try:
        job = pykube.Job.objects(api, namespace=args.namespace).get_by_name(
            args.name
        )
    except pykube.exceptions.ObjectDoesNotExist:
        sys.exit(f"Job {args.namespace}/{args.name} was not found!")
    purge_job_meta(job)
    job.delete(propagation_policy="Foreground")
    while job.exists():
        time.sleep(3)
    try:
        job.create()
    except Exception as e:
        sys.exit(f"Failed to create job {job.namespace}/{job.name}: {e}")
