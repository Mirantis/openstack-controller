#!/usr/bin/env python3
from concurrent import futures
import os
import time
import threading
import random
import datetime
import shutil

from openstack_controller.osctl.plugins import base
from openstack_controller.osctl.plugins import sosreport
from openstack_controller.osctl.plugins import constants
from openstack_controller import utils

LOG = utils.get_logger(__name__)
now = datetime.datetime.utcnow()


class SosReportShell(base.OsctlShell):
    name = "sos"
    description = "Collect sos report from deployment. Collects logs from Elastic, Kubernetes objects and low level data from backends."

    def build_options(self):
        sos_sub = self.pl_parser.add_subparsers(
            dest="sub_subcommand", required=True
        )

        logs_parser = sos_sub.add_parser(
            "report", help="Gather sos report for deployment."
        )

        logs_parser.add_argument(
            "--component",
            required=True,
            action="append",
            type=str,
            help=f"Name of component to create report for. Can be specified multiple times. List of known components: {list(constants.OSCTL_COMPONENT_LOGGERS.keys())}",
        )

        host_select_group = logs_parser.add_mutually_exclusive_group(
            required=True
        )
        host_select_group.add_argument(
            "--host",
            required=False,
            action="append",
            type=str,
            help="Name or label=value of kubernetes node to gather support dump for. Can be specified multiple times.",
        )
        host_select_group.add_argument(
            "--all-hosts",
            required=False,
            default=False,
            action="store_true",
            help="Gather support dump for all hosts",
        )

        elastic_group = logs_parser.add_argument_group(title="Elastic")
        elastic_group.add_argument(
            "--elastic-url",
            required=False,
            default="http://opensearch-master-headless.stacklight.svc.cluster.local:9200",
            type=str,
            help="Url to connect to elasticsearch service. By default is http://opensearch-master-headless.stacklight.svc.cluster.local:9200",
        )
        elastic_group.add_argument(
            "--elastic-username",
            required=False,
            type=str,
            help="Username for http authorization.",
        )
        elastic_group.add_argument(
            "--elastic-password",
            required=False,
            type=str,
            help="Password for http authorization.",
        )
        elastic_group.add_argument(
            "--elastic-index-name",
            default="logstash-*",
            type=str,
            help="Elastic search index name to look logs for.",
        )
        elastic_group.add_argument(
            "--elastic-query-size",
            required=False,
            type=int,
            default=10000,
            help="Number of documents to request from elastic in single query. By default is 10000.",
        )
        elastic_group.add_argument(
            "--since",
            required=False,
            type=str,
            default="1w",
            help=(
                "Defines timeframe for which take logs, is relative to current time."
                "Valid endings are: y: Years, M: Months, w: Weeks, d: Days, h or H: Hours, m: Minutes, s: Seconds. Default is 1w"
            ),
        )

        logs_parser.add_argument(
            "--workers-number",
            required=False,
            type=int,
            default=5,
            help="Number of workers to handle logs collection in parallel. Default is 5",
        )
        logs_parser.add_argument(
            "--workspace",
            required=False,
            type=str,
            default=f"/tmp/sosreport-{now.strftime('%Y%m%d%H%M%S')}",
            help="Dstination folder to store logs in.",
        )
        logs_parser.add_argument(
            "--no-archive",
            required=False,
            action="store_true",
            default=False,
            help="Archive report result",
        )
        logs_parser.add_argument(
            "--collector",
            required=False,
            action="append",
            type=str,
            choices=list(sosreport.registry.keys()),
            help="List of collectors to use in the dump. By default use all collectors.",
        )

    def progress(self, workspace, stop_event):
        while not stop_event.is_set():
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(workspace):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    # skip if it is symbolic link
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
            time.sleep(15)
            LOG.info(
                f"Still collecting logs. Current logs size is {total_size} bytes"
            )

    def report(self, args):
        tasks = []
        futures_list = []
        workspace = args.workspace
        for name, plugin in sosreport.registry.items():
            if args.collector and name not in set(args.collector):
                continue
            instance = plugin(args)
            tasks.extend(instance.get_tasks())
        random.shuffle(tasks)
        stop_event = threading.Event()
        with futures.ThreadPoolExecutor(
            max_workers=args.workers_number
        ) as executor:
            for task in tasks:
                LOG.debug(f"Submitting task {task}")
                future = executor.submit(task[0], *task[1], **task[2])
                futures_list.append(future)
            progress_thread = threading.Thread(
                target=self.progress, args=(args.workspace, stop_event)
            )
            progress_thread.daemon = True
            progress_thread.start()
            futures.wait(futures_list)
            stop_event.set()

        if args.no_archive:
            LOG.info(
                f"All tasks are completed. Sos report is saved to: {workspace}"
            )
        else:
            LOG.info(f"Archiving {workspace} directory")
            shutil.make_archive(workspace, "gztar", workspace)
            shutil.rmtree(workspace)
            LOG.info(
                f"All tasks are completed. Sos report is saved to: {workspace}.tar.gz"
            )
