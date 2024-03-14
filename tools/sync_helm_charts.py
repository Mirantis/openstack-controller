import yaml
import logging
import os
import requests

from openstack_controller import utils
from openstack_controller import layers
from openstack_controller import settings
from openstack_controller.constants import CHART_GROUP_MAPPING

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)

CHARTS_BASE_URL="https://artifactory.mcp.mirantis.net/artifactory/binary-dev-kaas-virtual"

artifacts = layers.render_binary_artifacts(CHARTS_BASE_URL)

for chart_group, charts in CHART_GROUP_MAPPING.items():
    repo_name = artifacts["common"][chart_group]["repo"]
    repo_url = [repo for repo in artifacts["common"]["charts"]["repositories"] if repo["name"] == repo_name][0]["url"]
    chart_version = artifacts["common"][chart_group]["releases"]["version"]
    dst = os.path.join(settings.HELM_CHARTS_DIR, chart_group)
    os.makedirs(dst, exist_ok=True)
    for chart in charts:
        chart_name = f"{chart}-{chart_version}.tgz"
        chart_url = f"{repo_url}/{chart_name}"
        dst_file = f"{dst}/{chart_name}"
        utils.download_file(chart_url, dst_file)
