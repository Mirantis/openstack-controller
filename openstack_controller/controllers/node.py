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

import dataclasses
import datetime

import kopf
import pykube

from openstack_controller import kube
from openstack_controller.services import base
from openstack_controller import settings
from openstack_controller import utils

LOG = utils.get_logger(__name__)

# Higher value means that component's prepare-usage handlers will be called
# later and prepare-shutdown handlers - sooner
COMPONENT_ORDER = {"compute": 100}


@dataclasses.dataclass
class StatusAnnotation:
    success_value: str
    failure_value: str
    in_progress_value: str = ""
    annotation_string: str = "workload.lcm.mirantis.com/openstack"


@dataclasses.dataclass
class WatchedAnnotation:
    watched_value: str
    status_annotation: StatusAnnotation = dataclasses.field(repr=False)
    annotation_string: str = "request.lcm.mirantis.com"


# NOTE(vdrok): we consider "status" value as a request to make sure
#              that the node is ready for use. Also there is no status'
#              in_progress_value for this case, according to the TASA-12
NODE_ADDITION_ANNOTATION = WatchedAnnotation(
    watched_value="status",
    status_annotation=StatusAnnotation(
        success_value="available", failure_value="not_available"
    ),
)


NODE_REMOVAL_ANNOTATION = WatchedAnnotation(
    watched_value="maintenance_mode",
    status_annotation=StatusAnnotation(
        success_value="ready",
        failure_value="not_ready",
        in_progress_value="preparing",
    ),
)


def _get_node_if_annotation_still_present(meta, annotation, value):
    # If it is a retry, check again that annotation is still present
    try:
        node = kube.find(pykube.Node, meta["name"])
    except pykube.KubernetesError:
        raise kopf.PermanentError(f"Node {meta['name']} was already deleted")
    if node.obj["metadata"].get("annotations", {}).get(annotation) != value:
        return None
    return node


def _patch_node_annotations(node, annotations, status):
    if not isinstance(annotations, list):
        annotations = [annotations]
    try:
        node.reload()
        p = {"metadata": {"annotations": {an: status for an in annotations}}}
        node.patch(p)
    except pykube.KubernetesError as e:
        raise kopf.PermanentError(
            f"Node {node.obj['metadata']['name']} was already deleted or "
            f"can not be updated: {e}"
        )


async def _run_methods_async(
    watched_annotation, components, await_attrs, meta, old, new
):
    watched_ann_string = watched_annotation.annotation_string
    watched_ann_value = watched_annotation.watched_value
    status_annotation = watched_annotation.status_annotation
    if (
        (old is None or old.get(watched_ann_string) != watched_ann_value)
        and new
        and new.get(watched_ann_string) == watched_ann_value
    ):
        node = _get_node_if_annotation_still_present(
            meta, watched_ann_string, watched_ann_value
        )
        if not node:
            return
        LOG.info(
            f"Handling node {meta['name']} "
            f"annotation {watched_annotation}."
        )
        if status_annotation.in_progress_value:
            _patch_node_annotations(
                node,
                status_annotation.annotation_string,
                status_annotation.in_progress_value,
            )
        # If one component fails, fail the whole process, as there is no
        # guarantee that next components do not depend on failed one
        for component, component_class in components:
            try:
                for method_name in await_attrs:
                    await getattr(component_class, method_name)(meta)
            except kopf.PermanentError:
                current_component = components.index(
                    (component, component_class)
                )
                _patch_node_annotations(
                    node,
                    [
                        "%s_%s" % (status_annotation.annotation_string, c[0])
                        for c in components[current_component:]
                    ]
                    + [status_annotation.annotation_string],
                    status_annotation.failure_value,
                )
                raise
        _patch_node_annotations(
            node,
            status_annotation.annotation_string,
            status_annotation.success_value,
        )


# TODO(vdrok): Consider a separate state reporting as described in
#              https://github.com/zalando-incubator/kopf/pull/331 if other
#              controllers want to watch the same field
@kopf.on.field("", "v1", "nodes", field="metadata.annotations")
async def node_set_annotation_handler(meta, old, new, **kwargs):
    ordered_components = sorted(
        filter(
            lambda tup: tup[0] in COMPONENT_ORDER,
            base.Service.registry.items(),
        ),
        key=lambda tup: COMPONENT_ORDER[tup[0]],
    )
    await _run_methods_async(
        NODE_ADDITION_ANNOTATION,
        ordered_components,
        ["prepare_node_after_reboot", "add_node_to_scheduling"],
        meta,
        old,
        new,
    )
    await _run_methods_async(
        NODE_REMOVAL_ANNOTATION,
        list(reversed(ordered_components)),
        ["remove_node_from_scheduling", "prepare_for_node_reboot"],
        meta,
        old,
        new,
    )


@kopf.on.field("", "v1", "nodes", field="status.conditions")
@utils.collect_handler_metrics
async def node_status_update_handler(name, body, old, new, event, **kwargs):
    LOG.debug(f"Handling node status {event} event.")
    LOG.debug(f"The new state is {new}")

    # NOTE(vsaienko) get conditions from the object to avoid fake reporing by
    # calico when kubelet is down on the node.
    # Do not remove pods from flapping node.
    node = kube.Node(kube.api, body)
    if node.ready:
        return True

    not_ready_delta = datetime.timedelta(
        seconds=settings.OSCTL_NODE_NOT_READY_FLAPPING_TIMEOUT
    )

    now = last_transition_time = datetime.datetime.utcnow()

    for cond in node.obj["status"]["conditions"]:
        if cond["type"] == "Ready":
            last_transition_time = datetime.datetime.strptime(
                cond["lastTransitionTime"], "%Y-%m-%dT%H:%M:%SZ"
            )
    not_ready_for = now - last_transition_time
    if now - not_ready_delta < last_transition_time:
        raise kopf.TemporaryError(
            f"The node is not ready for {not_ready_for.seconds}s",
        )
    LOG.info(
        f"The node: {name} is not ready for {not_ready_for.seconds}s. "
        f"Removing pods..."
    )
    node.remove_pods(settings.OSCTL_OS_DEPLOYMENT_NAMESPACE)
