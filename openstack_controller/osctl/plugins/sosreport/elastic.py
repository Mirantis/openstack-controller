#!/usr/bin/env python3

import os

from opensearchpy import OpenSearch

from openstack_controller.osctl.plugins.sosreport import base
from openstack_controller.osctl import utils as osctl_utils
from openstack_controller import utils

LOG = utils.get_logger(__name__)


class ElasticLogsCollector(base.BaseLogsCollector):
    name = "elastic"

    def __init__(self, args):
        self.elastic_url = args.elastic_url
        self.elastic_query_size = args.elastic_query_size
        self.elastic_index_name = "logstash-*"
        self.workspace = os.path.join(args.workspace, "elastic")
        self.hosts = set(args.host)
        self.components = set(args.component)
        self.since = args.since

    def query_logger(self, component):
        return {
            "bool": {
                "should": [
                    {
                        "query_string": {
                            "fields": ["logger"],
                            "query": f"{component}\\-*",
                        }
                    }
                ],
                "minimum_should_match": 1,
            }
        }

    def query_host(self, host):
        return {
            "bool": {
                "should": [{"match": {"kubernetes.host": host}}],
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

    def get_query(self, host, component, since="1w"):
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
                    "filter": [
                        {"match_all": {}},
                        self.query_host(host),
                        self.query_logger(component),
                        self.query_timestamp(since),
                    ],
                    "should": [],
                    "must_not": [],
                }
            },
        }

    @osctl_utils.generic_exception
    def collect_logs(self, host, component, since="1w"):
        LOG.info(f"Starting logs collection for {host} {component}")
        client = OpenSearch([self.elastic_url], timeout=60, http_compress=True)
        query = self.get_query(host, component, since)
        response = client.search(
            body=query, index=self.elastic_index_name, request_timeout=60
        )
        os.makedirs(os.path.join(self.workspace, host), exist_ok=True)
        while len(response["hits"]["hits"]):
            for hit in response["hits"]["hits"]:
                ts = hit["_source"]["@timestamp"]
                level = hit["_source"].get("severity_label", "UNKNOWN")
                message = hit["_source"].get("message", "UNCNOWN")
                pod_name = hit["_source"]["kubernetes"]["pod_name"]
                logs_dst = os.path.join(self.workspace, host, pod_name)
                msg = f"{ts} {level} {message}"
                with open(logs_dst, "a") as f:
                    f.write(msg)
                    if not msg.endswith("\n"):
                        f.write("\n")
            search_after = response["hits"]["hits"][-1]["sort"]
            query["search_after"] = search_after
            response = client.search(body=query, index=self.elastic_index_name)
        LOG.info(f"Successfully collected logs for {host} {component}")

    def get_tasks(self):
        res = []
        for host in self.hosts:
            for component in self.components:
                res.append(
                    (
                        self.collect_logs,
                        (host, component),
                        {"since": self.since},
                    )
                )
        return res
