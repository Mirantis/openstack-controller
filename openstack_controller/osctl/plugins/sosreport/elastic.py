#!/usr/bin/env python3

import os

from opensearchpy import OpenSearch

from openstack_controller.osctl.plugins import constants
from openstack_controller.osctl.plugins.sosreport import base
from openstack_controller.osctl import utils as osctl_utils
from openstack_controller import utils

LOG = utils.get_logger(__name__)


class ElasticLogsCollector(base.BaseLogsCollector):
    name = "elastic"

    def __init__(self, args, workspace):
        super().__init__(args, workspace)
        self.elastic_url = args.elastic_url
        self.elastic_query_size = args.elastic_query_size
        self.elastic_index_name = args.elastic_index_name
        self.loggers = self.get_loggers(self.components)
        self.since = args.since
        self.http_auth = None
        if self.args.elastic_username and self.args.elastic_password:
            self.http_auth = (
                self.args.elastic_username,
                self.args.elastic_password,
            )

    def get_hosts(self):
        if self.args.all_hosts:
            # NOTE(vsaienko): skip discovery via kubernetes
            # get host directly from elastic/opensearch.
            return [None]
        return super().get_hosts()

    def get_loggers(self, components):
        loggers = set()
        for component in set(components):
            for logger in constants.OSCTL_COMPONENT_LOGGERS.get(
                component, [component]
            ):
                loggers.add(logger)
        return loggers

    def query_logger(self, logger):
        return {
            "bool": {
                "should": [
                    {
                        "query_string": {
                            "fields": ["logger"],
                            "query": f"{logger}*",
                        }
                    }
                ],
                "minimum_should_match": 1,
            }
        }

    def query_host(self, host):
        return {
            "bool": {
                "should": [{"match_phrase": {"kubernetes.host": host}}],
                "minimum_should_match": 1,
            }
        }

    def query_timestamp(self, since="1w"):
        """Returns opensearch timestamp based on input since

        Valid endings:
           y: Years
           M: Months
           w: Weeks
           d: Days
           h or H: Hours
           m: Minutes
           s: Seconds
        https://opensearch.org/docs/2.0/opensearch/supported-field-types/date/
        """
        return {"range": {"@timestamp": {"gte": f"now-{since}"}}}

    def get_query(self, logger, host=None, since="1w"):
        filters = [
            {"match_all": {}},
            self.query_logger(logger),
            self.query_timestamp(since),
        ]
        if host is not None:
            filters.append(self.query_host(host))
        return {
            "size": self.elastic_query_size,
            "sort": [
                {
                    "@timestamp": {
                        "order": "asc",
                    }
                }
            ],
            "query": {
                "bool": {
                    "must": [],
                    "filter": filters,
                    "should": [],
                    "must_not": [],
                }
            },
        }

    @osctl_utils.generic_exception
    def collect_logs(self, logger, host=None, since="1w"):
        msg = f"Starting logs collection for {host} {logger}"
        if host is None:
            msg = f"Starting logs collection for all hosts {logger}"
        LOG.info(msg)
        client = OpenSearch(
            [self.elastic_url],
            timeout=60,
            http_auth=self.http_auth,
            http_compress=True,
        )
        query = self.get_query(logger, host=host, since=since)
        response = client.search(
            body=query, index=self.elastic_index_name, request_timeout=60
        )
        while len(response["hits"]["hits"]):
            for hit in response["hits"]["hits"]:
                ts = hit["_source"]["@timestamp"]
                level = hit["_source"].get("severity_label", "UNKNOWN")
                message = hit["_source"].get("message", "UNCNOWN")
                source_kubernetes = hit["_source"].get("kubernetes")
                if not source_kubernetes:
                    continue
                pod_name = source_kubernetes.get("pod_name", "UNCNOWN")
                container_name = source_kubernetes.get(
                    "container_name", "UNCNOWN"
                )
                host = source_kubernetes.get("host", "UNKNOWN")
                logs_dst_base = os.path.join(self.workspace, host, pod_name)
                os.makedirs(logs_dst_base, exist_ok=True)
                logs_dst = os.path.join(
                    self.workspace, host, pod_name, container_name
                )
                msg = f"{ts} {level} {message}"
                with open(logs_dst, "a") as f:
                    f.write(msg)
                    if not msg.endswith("\n"):
                        f.write("\n")
            search_after = response["hits"]["hits"][-1]["sort"]
            query["search_after"] = search_after
            response = client.search(body=query, index=self.elastic_index_name)
        LOG.info(f"Successfully collected logs for {host} {logger}")

    def get_tasks(self):
        res = []
        for host in self.hosts:
            for logger in self.loggers:
                res.append(
                    (
                        self.collect_logs,
                        (logger,),
                        {"host": host, "since": self.since},
                    )
                )
        return res
