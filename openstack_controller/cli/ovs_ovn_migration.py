#!/usr/bin/env python3
import asyncio
import argparse
import traceback
import json
import re
import time

from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from pykube import ConfigMap

from openstack_controller import constants
from openstack_controller import health
from openstack_controller import helm
from openstack_controller import kube
from openstack_controller import utils
from openstack_controller import osdplstatus
from openstack_controller import resource_view
from openstack_controller import services
from openstack_controller import settings
from openstack_controller.openstack_utils import OpenStackClientManager


LOG = utils.get_logger(__name__)

MIGRATION_FINALIZER = "lcm.mirantis.com/ovs-ovn-migration.finalizer"
MIGRATION_STATE_CONFIGMAP_NAME = "ovs-ovn-migration-state"

# Stage statuses
STARTED, COMPLETED, FAILED = ("started", "completed", "failed")


def set_args():
    parser = argparse.ArgumentParser(
        prog="osctl-ovs-ovn-migrate",
        description="Migrate from OVS neutron backend to OVN.",
    )
    subparsers = parser.add_subparsers(
        help="Parse subcommands of migration script", dest="mode"
    )
    subparsers.add_parser(
        "backup_db", help="Backup Neutron database before migration"
    )
    migrate_subparcer = subparsers.add_parser(
        "migration",
        help="Start migration process",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers.add_parser(
        "preflight_checks", help="OpenStack checks before migration"
    )
    migrate_subparcer.add_argument(
        "--non-interactive",
        action="store_false",
        dest="interactive",
        help=("Run migration in non interactive mode"),
    )
    migrate_subparcer.add_argument(
        "--max-workers",
        type=int,
        default=0,
        dest="max_workers",
        help=(
            """Maximum number of workers to spawn for parallel operations.
            If set to 0, internal defaults for operations will be used.
            For example for pods parallel operations (like exec) number of workers will be
            equal to number of target pods.
            """
        ),
    )
    migrate_subparcer.add_argument(
        "--cmp-threshold",
        type=int,
        default=0,
        dest="cmp_threshold",
        help="Maximum number of compute nodes allowed to fail migration.",
    )
    migrate_subparcer.add_argument(
        "--gtw-threshold",
        type=int,
        default=0,
        dest="gtw_threshold",
        help="Maximum number of gateway nodes allowed to fail migration.",
    )

    args = parser.parse_args()
    if not args.mode:
        parser.error("Run mode does not specified")
    return args


def check_input(check, msg, error_string="Illegal Input"):
    while True:
        result = input(f"[USER INPUT NEEDED] {msg} --> ").strip()
        if check(result):
            return result
        LOG.error(error_string)


class StateCM:

    labels = {"lcm.mirantis.com/ovs-ovn-migration": "state"}

    def __init__(self, name, namespace, stages):
        self.name = name
        self.namespace = namespace
        cm = [
            cm
            for cm in kube.resource_list(
                ConfigMap,
                self.labels,
                namespace=namespace,
            )
        ]
        if len(cm) > 1:
            raise ValueError("Found more than one existing state configmap")
        if not cm:
            LOG.info("State configmap does not exist, creating")
            self.cm = self.create(stages)
        else:
            LOG.warning("State configmap already exists")
            self.cm = cm[0]

    def create(self, stages):
        """Create configmap in format:
        <stage1_name>: '{"status": "init", "error": null}'
        <stage2_name>: '{"status": "init", "error": null}'
        and returns k8s configmap object
        """
        stage_init_state = {"status": "init", "error": None}
        state_cm = kube.dummy(
            ConfigMap,
            self.name,
            namespace=self.namespace,
        )
        state_cm.metadata["labels"] = self.labels
        state_cm.obj["data"] = {
            stage["name"]: json.dumps(stage_init_state) for stage in stages
        }
        state_cm.create()
        return state_cm

    @property
    def state(self):
        self.cm.reload()
        cm_data = self.cm.obj.get("data", {})
        data = {k: json.loads(v) for k, v in cm_data.items()}
        return data

    def update(self, stage, status, error=None):
        state = self.state
        state[stage] = {"status": status, "error": error}
        self.cm.obj["data"] = {k: json.dumps(v) for k, v in state.items()}
        self.cm.update(is_strategic=False)


def get_network_service(osdpl):
    osdpl.reload()
    mspec = osdpl.mspec
    child_view = resource_view.ChildObjectView(mspec)
    osdplst = osdplstatus.OpenStackDeploymentStatus(
        osdpl.name, osdpl.namespace
    )
    network_svc = services.registry["networking"](
        mspec, LOG, osdplst, child_view
    )
    return network_svc


def get_objects_by_id(svc, id):
    # switch case is supported from python 3.10
    if id == "openvswitch-ovn-db":
        return [svc.get_child_object("StatefulSet", "openvswitch-ovn-db")]
    elif id == "openvswitch-ovn-northd":
        return [svc.get_child_object("StatefulSet", "openvswitch-ovn-northd")]
    elif id == "ovn-controller":
        return svc.get_child_objects_dynamic("DaemonSet", "ovn-controller")
    elif id == "openvswitch-vswitchd":
        return svc.get_child_objects_dynamic(
            "DaemonSet", "openvswitch-vswitchd"
        )
    elif id == "neutron-ovs-agent":
        return svc.get_child_objects_dynamic("DaemonSet", "neutron-ovs-agent")
    elif id == "neutron-l3-agent":
        return svc.get_child_objects_dynamic("DaemonSet", "neutron-l3-agent")
    elif id == "neutron-ovn-db-sync-migrate":
        return [svc.get_child_object("Job", "neutron-ovn-db-sync-migrate")]
    elif id == "neutron-metadata-agent":
        return svc.get_child_objects_dynamic(
            "DaemonSet", "neutron-metadata-agent"
        )
    else:
        raise ValueError("Unknown object id {id}")


def update_service_release(hm, service, release_name, patch):
    """Updates only specified release for service with patched values"""
    bundle = service.render()
    for release in bundle["spec"]["releases"]:
        if release["name"] == release_name:
            utils.merger.merge(release["values"], patch)
            bundle["spec"]["releases"] = [release]
            break
    asyncio.run(hm.install_bundle(bundle))


def wait_for_objects_ready(service, object_ids, timeout=1200):
    """
    Waits for child objects of the service to be ready

    :param service: Object of type Service
    :param object_ids: List of strings
    :returns None
    """
    LOG.info(f"Waiting for {object_ids} to be ready")
    for id in object_ids:
        for obj in get_objects_by_id(service, id):
            asyncio.run(obj.wait_ready(timeout=timeout))
    LOG.info(f"{object_ids} are ready")


def daemonsets_check_exec(results, raise_on_error=True):
    failed_nodes = []
    for res in results:
        LOG.debug(
            f"""
        DaemonSet {res['daemonset']} Pod {res['pod']}:{res['container']} exec results:
            NODE:
              {res['node']}
            COMMAND:
              {res['command']}
            STATUS:
              {res['status']}
            STDERR:
              {res['stderr']}
            STDOUT:
              {res['stdout']}
            ERROR:
              {res['error_json']}
            EXCEPTION:
              {res['exception']}
        """
        )
        if res["status"] != "Success":
            failed_nodes.append(res["node"])
    if failed_nodes:
        LOG.error(f"Failed to execute command on nodes {failed_nodes}")
        if raise_on_error:
            raise RuntimeError("Failed to run exec for daemonsets")


def daemonsets_exec_parallel(
    daemonsets,
    command,
    container,
    max_workers=0,
    timeout=30,
    raise_on_error=True,
    nodes=None,
):
    """Run exec inside pods of different daemonsets in parallel
    :param daemonsets: List of kube.DaemonSet objects
    :param command: List of strings
    :param container: String with name of container chosen for command execution
    :param max_workers: Integer number of max parallel threads to spawn
    :param timeout: timeout for command execution inside pod.
    :param nodes: List of nodes selected to run command. If set, command will
                  be run only in pods on specified nodes.
    :returns List of dictionnaries in format
    """
    pods_map = {}
    pods = []
    for ds in daemonsets:
        pods_map[ds] = ds.pods
        pods.extend(pods_map[ds])
    if not max_workers:
        max_workers = len(pods)
    if nodes:
        pods = [
            pod for pod in pods if pod.obj["spec"].get("nodeName") in nodes
        ]
    # Maximum time to wait for all workers to finish
    pool_timeout = len(pods) * timeout
    args = [command]
    kwargs = {
        "container": container,
        "raise_on_error": False,
        "timeout": timeout,
    }
    future_data = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        LOG.info(
            f"Running command {command} on pods of daemonsets {daemonsets}"
        )
        for pod in pods:
            future = executor.submit(pod.exec, *args, **kwargs)
            future_data[pod] = future
        LOG.info(f"Waiting command on pods of daemonsets {daemonsets}")
        done, not_done = wait(
            future_data.values(),
            return_when=ALL_COMPLETED,
            timeout=pool_timeout,
        )
        LOG.info(f"Done waiting command on pods of daemonsets {daemonsets}")
    results = []
    for pod, future in future_data.items():
        for ds in daemonsets:
            if pod in pods_map[ds]:
                pod_ds = ds
        data = {
            "daemonset": pod_ds.name,
            "node": pod.obj["spec"].get("nodeName"),
            "pod": pod.name,
            "container": container,
            "command": command,
            "error_json": {},
            "exception": None,
            "stderr": "",
            "stdout": "",
            "status": "Unknown",
        }
        if future in done:
            result = future.result()
            data["error_json"] = result["error_json"]
            data["exception"] = result["exception"]
            data["stderr"] = result["stderr"]
            data["stdout"] = result["stdout"]
            if result["timed_out"]:
                data["status"] = "Timed_out"
            elif result["exception"]:
                data["status"] = "Failure"
            elif "status" in data["error_json"]:
                data["status"] = data["error_json"]["status"]
        elif future in not_done:
            data["status"] = "Pool_timed_out"
        results.append(data)
    daemonsets_check_exec(results, raise_on_error)
    return results


def check_nodes_results(results, role, threshold):
    """Check results list according to failed nodes threshold and node role.

    :param results: List of maps with command execution results on nodes
    :param role: NodeRole object
    :param threshold: Integer number of nodes which are allowed to fail migration
    :returns: tuple with failed nodes set and boolean result of threshold check
    """
    failed_nodes = set()
    threshold_fail = False
    for res in results:
        kube_node = kube.safe_get_node(res["node"])
        if kube_node.has_role(role):
            if res["status"] != "Success":
                failed_nodes.add(res["node"])
    if failed_nodes:
        LOG.warning(
            f"Got failed command results on next {role.name} nodes: {failed_nodes}"
        )
        if len(failed_nodes) <= threshold:
            LOG.warning(
                f"Number of {role.name} nodes {len(failed_nodes)} doesn't exceed threshold {threshold}."
            )
        else:
            LOG.error(
                f"Number of {role.name} nodes {len(failed_nodes)} exceeds threshold {threshold}."
            )
            threshold_fail = True
    return failed_nodes, threshold_fail


def cleanup_api_resources():
    """Cleanup resources from Openstack API related to neutron ovs backend"""
    ocm = OpenStackClientManager()
    LOG.info("Starting Neutron API resources cleanup")
    for device_owner in [
        "network:dhcp",
        "network:router_ha_interface",
        "network:floatingip_agent_gateway",
    ]:
        LOG.info(f"Cleaning Neutron {device_owner} ports")
        try:
            ocm.network_ensure_ports_absent(device_owner)
        except Exception:
            LOG.exception(f"Failed to clean some {device_owner} ports")
        LOG.info(f"Finished cleaning Neutron {device_owner} ports")
    for agent_type in [
        "Open vSwitch agent",
        "DHCP agent",
        "L3 agent",
        "Metadata agent",
    ]:
        LOG.info(f"Cleaning Neutron {agent_type} agents")
        for agent in ocm.network_get_agents(agent_type=agent_type):
            try:
                ocm.oc.network.delete_agent(agent)
            except Exception:
                LOG.exception(f"Failed to clean agent {agent}")
        LOG.info(f"Finished cleaning Neutron {agent_type} agents")
    for net in ocm.oc.network.networks():
        if re.match("^HA network tenant\s", net.name):
            LOG.info(f"Cleaning Neutron HA tenant network {net.name}")
            try:
                ocm.oc.network.delete_network(net)
            except Exception:
                LOG.exception(f"Failed to clean network {net.name}")
            LOG.info(f"Finished cleaning Neutron HA tenant network {net.name}")
    LOG.info("Finished Neutron API resources cleanup")


def cleanup_ovs_bridges(script_args):
    """Cleanup OVS interfaces, bridges on nodes"""
    osdpl = kube.get_osdpl()
    network_svc = get_network_service(osdpl)
    metadata_daemonsets = get_objects_by_id(
        network_svc, "neutron-metadata-agent"
    )
    cleanup_ovs_command = """
    set -ex
    trap err_trap EXIT
    function err_trap {
        local r=$?
        if [[ $r -ne 0 ]]; then
            echo "cleanup_ovs FAILED"
        fi
        exit $r
    }
    OVS_DB_SOCK="--db=tcp:127.0.0.1:6640"
    ovs-vsctl ${OVS_DB_SOCK} --if-exists del-br br-tun
    echo "Remove tunnel and migration bridges"
    ovs-vsctl ${OVS_DB_SOCK} --if-exists del-br br-migration
    ovs-vsctl ${OVS_DB_SOCK} --if-exists del-port br-int patch-tun
    echo "Cleaning all migration fake bridges"
    for br in $(egrep '^migbr-' <(ovs-vsctl ${OVS_DB_SOCK} list-br)); do
        ovs-vsctl ${OVS_DB_SOCK} del-br $br
    done
    """
    LOG.info("Cleaning OVS bridges")
    daemonsets_exec_parallel(
        metadata_daemonsets,
        ["bash", "-c", cleanup_ovs_command],
        "neutron-metadata-agent",
        max_workers=script_args.max_workers,
        timeout=120,
    )
    LOG.info("Finished cleaning OVS bridges")


def cleanup_linux_netns(script_args):
    """Cleanup linux network namespaces and
    related network interfaces
    """
    osdpl = kube.get_osdpl()
    network_svc = get_network_service(osdpl)
    metadata_daemonsets = get_objects_by_id(
        network_svc, "neutron-metadata-agent"
    )
    cleanup_netns_command = """
    set -ex
    trap err_trap EXIT
    function err_trap {
        local r=$?
        if [[ $r -ne 0 ]]; then
            echo "cleanup_netns FAILED"
        fi
        exit $r
    }
    OVS_DB_SOCK="--db=tcp:127.0.0.1:6640"
    IP_NETNS="sudo neutron-rootwrap /etc/neutron/rootwrap.conf ip netns"
    EXIT_CODE=0
    for ns in $(egrep 'qrouter-|qdhcp-|snat-|fip-' <(cut -d' ' -f1 <($IP_NETNS))); do
        for link in $(cut -d: -f2 <(grep -v LOOPBACK <($IP_NETNS exec $ns ip -o link show))); do
            $IP_NETNS exec $ns ip l delete $link || ovs-vsctl ${OVS_DB_SOCK} --if-exists del-port br-int $link
        done
        if [[ -n $(grep -v LOOPBACK <($IP_NETNS exec $ns ip -o link show)) ]]; then
            echo "Failed to clean all interfaces in network namespace $ns, namespace will not be removed"
            EXIT_CODE=1
        else
            echo "Cleaned all interfaces in network namespace $ns, removing namespace"
            $IP_NETNS delete $ns
        fi
    done
    exit "${EXIT_CODE}"
    """
    # using timeout 1200 as neutron-rootwrap takes a lot of time
    LOG.info("Cleaning network namespaces")
    daemonsets_exec_parallel(
        metadata_daemonsets,
        ["bash", "-c", cleanup_netns_command],
        "neutron-metadata-agent",
        max_workers=script_args.max_workers,
        timeout=1200,
    )
    LOG.info("Finished cleaning network namespaces")


def prepare(script_args):
    osdpl = kube.get_osdpl()
    network_svc = get_network_service(osdpl)
    LOG.info("Backing up OVS bridge mappings")
    backup_bridge_mappings = """
    set -ex
    trap err_trap EXIT
    function err_trap {
        local r=$?
        if [[ $r -ne 0 ]]; then
            echo "prepare FAILED"
        fi
        exit $r
    }
    echo "Getting original bridge mapping"
    bm=$(cut -d= -f2 <(grep bridge_mappings /etc/neutron/plugins/ml2/openvswitch_agent.ini))
    [[ -z $bm ]] && echo bridge_mappings is empty! && exit 1
    echo "Original bridge mapping is ${bm}"
    ovs-vsctl set Open_Vswitch . external-ids:ovn-bridge-mappings-back="${bm// /}"
    echo "Finished original bridge mapping backup"
    """
    neutron_ovs_agents = get_objects_by_id(network_svc, "neutron-ovs-agent")
    daemonsets_exec_parallel(
        neutron_ovs_agents,
        ["bash", "-c", backup_bridge_mappings],
        "neutron-ovs-agent",
        max_workers=script_args.max_workers,
    )


def deploy_ovn_db(script_args):
    osdpl = kube.get_osdpl()
    network_svc = get_network_service(osdpl)
    LOG.info(
        "Modifying openvswitch and neutron-l3-agent finalizers to prevent early deletion"
    )
    for daemonset in ["openvswitch-vswitchd", "neutron-l3-agent"]:
        for ds in get_objects_by_id(network_svc, daemonset):
            LOG.info(
                f"Adding finalizer {MIGRATION_FINALIZER} to DaemonSet {ds}"
            )
            ds.ensure_finalizer_present(MIGRATION_FINALIZER)

    LOG.info("Patching Openstack deployment to deploy ovn database")
    osdpl.patch(
        {
            "spec": {
                "migration": {
                    "neutron": {"ovs_ovn_migration": True},
                },
                "features": {"neutron": {"backend": "ml2/ovn"}},
                "services": {
                    "networking": {
                        "neutron": {
                            "values": {
                                "manifests": {
                                    "deployment_server": False,
                                }
                            }
                        },
                        "openvswitch": {
                            "values": {
                                "manifests": {
                                    "daemonset_ovn_controller": False
                                }
                            }
                        },
                    }
                },
            }
        }
    )
    # https://mirantis.jira.com/browse/PRODX-42146
    time.sleep(30)
    asyncio.run(osdpl.wait_applied())
    network_svc = get_network_service(osdpl)
    wait_for_objects_ready(
        network_svc,
        ["openvswitch-ovn-db", "openvswitch-ovn-northd"],
    )
    LOG.info("Deployment OVN db done")


def deploy_ovn_controllers(script_args):
    """Deploys ovn controllers in migration mode and syncs ovn db"""
    osdpl = kube.get_osdpl()
    network_svc = get_network_service(osdpl)
    ovn_daemonsets = get_objects_by_id(network_svc, "ovn-controller")
    helm_manager = helm.HelmManager(namespace=osdpl.namespace)
    osdpl.patch({"spec": {"draft": True}})
    if not ovn_daemonsets:
        LOG.info("Deploying ovn controllers in migration mode")
        ovs_patch = {
            "conf": {
                "ovn_migration": True,
            },
            "manifests": {"daemonset_ovn_controller": True},
        }
        update_service_release(
            helm_manager,
            network_svc,
            "openstack-openvswitch",
            ovs_patch,
        )
        # ovn controllers should be already running and ready before we running ovn db sync
        wait_for_objects_ready(
            network_svc,
            ["openvswitch-ovn-db", "openvswitch-ovn-northd", "ovn-controller"],
        )
    LOG.info("Starting Neutron database sync to OVN database")
    neutron_patch = {"manifests": {"job_ovn_db_sync_migrate": True}}
    update_service_release(
        helm_manager, network_svc, "openstack-neutron", neutron_patch
    )
    # On large environments ovn db sync can take a lot of time
    wait_for_objects_ready(network_svc, ["neutron-ovn-db-sync-migrate"])
    LOG.info("Neutron database sync to OVN database is completed")


def migrate_dataplane(script_args):
    osdpl = kube.get_osdpl()
    network_svc = get_network_service(osdpl)
    ovn_daemonsets = get_objects_by_id(network_svc, "ovn-controller")
    LOG.info(
        "Pre-migration check: Checking ovs db connectivity in ovn controllers"
    )
    try:
        daemonsets_exec_parallel(
            ovn_daemonsets,
            ["ovs-vsctl", "--no-wait", "list-br"],
            "controller",
            max_workers=script_args.max_workers,
        )
    except Exception as e:
        LOG.error(
            f"Failed Pre-migration check, fix issues and rerun migrate_dataplane stage"
        )
        raise e
    LOG.info("Pre-migration check: Ovs db connectivity check completed")

    tries = 0
    failed_nodes = set()
    gtw_threshold_fail = False
    cmp_threshold_fail = False
    while tries < 3:
        results = daemonsets_exec_parallel(
            ovn_daemonsets,
            ["/tmp/ovn-migrate-dataplane.sh"],
            "controller",
            max_workers=script_args.max_workers,
            raise_on_error=False,
            timeout=60,
            nodes=failed_nodes,
        )
        failed_nodes = set()
        failed_gtw, gtw_threshold_fail = check_nodes_results(
            results, constants.NodeRole.gateway, script_args.gtw_threshold
        )
        failed_cmp, cmp_threshold_fail = check_nodes_results(
            results, constants.NodeRole.compute, script_args.cmp_threshold
        )
        failed_nodes = failed_gtw.union(failed_cmp)
        tries += 1
        if not (gtw_threshold_fail or cmp_threshold_fail):
            break
    if gtw_threshold_fail or cmp_threshold_fail:
        LOG.error(
            f"""Still have failed nodes thresholds exceeded after {tries} retries,
            Stage will be marked as failed, if decided to rerun whole script, this
            stage will be rerun.
            """
        )
        raise RuntimeError("Failed nodes thresholds exceeded")
    elif failed_nodes:
        LOG.warning(
            f"""Still have some failed nodes after {tries} retries,
            Stage will be marked as completed, if decided to rerun whole script, this
            stage will be NOT rerun.
            """
        )


def finalize_migration(script_args):
    osdpl = kube.get_osdpl()
    network_svc = get_network_service(osdpl)
    LOG.info("Turning off ovn controller pods migration mode")
    osdpl.patch(
        {
            "spec": {
                "draft": False,
                "services": {
                    "networking": {
                        "openvswitch": {
                            "values": {
                                "manifests": {"daemonset_ovn_controller": True}
                            }
                        }
                    }
                },
            }
        }
    )
    # https://mirantis.jira.com/browse/PRODX-42146
    time.sleep(30)
    asyncio.run(osdpl.wait_applied())
    wait_for_objects_ready(
        network_svc, ["openvswitch-ovn-db", "openvswitch-ovn-northd"]
    )
    neutron_l3_daemonsets = get_objects_by_id(network_svc, "neutron-l3-agent")
    vswitchd_daemonsets = get_objects_by_id(
        network_svc, "openvswitch-vswitchd"
    )
    ovn_daemonsets = get_objects_by_id(network_svc, "ovn-controller")
    for ovs_ds in vswitchd_daemonsets:
        for ovs_pod in ovs_ds.pods:
            node = ovs_pod.obj["spec"].get("nodeName")
            LOG.info(f"Found ovs pod on node {node}")
            for ovn_ds in ovn_daemonsets:
                if ovn_ds.get_pod_on_node(node):
                    LOG.info(f"Removing ovs pod {ovs_pod} on node {node}")
                    ovs_pod.delete(propagation_policy="Background")
                    LOG.info(f"Updating ovn pod on node {node}")
                    asyncio.run(ovn_ds.ensure_pod_generation_on_node(node))
                    LOG.info(f"Updated ovn pod on node {node}")
                    break

    # Remove unused DaemonSets
    # TODO: add waiter that no ds are left
    for ds_list in [neutron_l3_daemonsets, vswitchd_daemonsets]:
        for ds in ds_list:
            LOG.info(f"Removing DaemonSet {ds}")
            ds.ensure_finalizer_absent(MIGRATION_FINALIZER)
    # Enable neutron-server and disable migration in osdpl
    LOG.info("Patching Openstack deployment to deploy neutron-server")
    osdpl.patch(
        {
            "spec": {
                "migration": {
                    "neutron": {"ovs_ovn_migration": False},
                },
                "services": {
                    "networking": {
                        "neutron": {
                            "values": {
                                "manifests": {
                                    "deployment_server": True,
                                }
                            }
                        },
                    }
                },
            }
        }
    )
    # https://mirantis.jira.com/browse/PRODX-42146
    time.sleep(30)
    asyncio.run(osdpl.wait_applied())
    mspec = osdpl.mspec
    child_view = resource_view.ChildObjectView(mspec)
    osdplst = osdplstatus.OpenStackDeploymentStatus(
        osdpl.name, osdpl.namespace
    )
    asyncio.run(health.wait_services_healthy(osdpl.mspec, osdplst, child_view))


def cleanup(script_args):
    cleanup_api_resources()
    cleanup_ovs_bridges(script_args)
    cleanup_linux_netns(script_args)


WORKFLOW = [
    {
        "executable": prepare,
        "name": "10_PREPARE",
        "impact": """
            WORKLOADS: No downtime expected.
            OPENSTACK API: No downtime expected.""",
        "description": """
            Check pre-requisites, backup bridge mappings on nodes.""",
    },
    {
        "executable": deploy_ovn_db,
        "name": "20_DEPLOY_OVN_DB",
        "impact": """
            WORKLOADS: No downtime expected.
            OPENSTACK API: Neutron API downtime starts in this stage.""",
        "description": """
            Deploy OVN with only database components enabled,
            Disable neutron server and all neutron components except L3 agents.""",
    },
    {
        "executable": deploy_ovn_controllers,
        "name": "30_DEPLOY_OVN_CONTROLLERS",
        "impact": """
            WORKLOADS: No downtime expected.
            OPENSTACK API: Neutron API downtime continues in this stage.""",
        "description": """
            Deploy OVN controllers in migration mode.
            Sync neutron database with flag migrate to OVN database
            (requires ovn controllers to be running and ready).""",
    },
    {
        "executable": migrate_dataplane,
        "name": "40_MIGRATE_DATAPLANE",
        "impact": """
            WORKLOADS: Short periods of downtime ARE EXPECTED.
            OPENSTACK API: Neutron API downtime continues in this stage.""",
        "description": """
            Deploy OVN controller on the same nodes as openvswitch pods are running.
            Switch dataplane to be managed by OVN controller.""",
    },
    {
        "executable": finalize_migration,
        "name": "50_FINALIZE_MIGRATION",
        "impact": """
            WORKLOADS: Short periods of downtime ARE EXPECTED.
            OPENSTACK API: Neutron API downtime stops in this stage.""",
        "description": """
            Stop openvswitch pods and disbale migration mode (switch ovn
            controllers to start own vswitchd and ovs db containers).
            Remove neutron l3 agent daemonsets.
            Enable Neutron server.""",
    },
    {
        "executable": cleanup,
        "name": "60_CLEANUP",
        "impact": """
            WORKLOADS: No downtime expected.
            OPENSTACK API: No downtime expected.""",
        "description": """
            Cleanup OVS leftovers in Openstack API.
            Remove not used OVS interfaces and linux network namespaces.""",
    },
]


def do_migration(script_args):
    state_cm = StateCM(
        MIGRATION_STATE_CONFIGMAP_NAME,
        settings.OSCTL_OS_DEPLOYMENT_NAMESPACE,
        WORKFLOW,
    )
    state = state_cm.state
    LOG.info(f"Initial migration state is {state}")
    for stage in WORKFLOW:
        stage_name = stage["name"]
        error = None
        try:
            if state[stage_name]["status"] == COMPLETED:
                LOG.info(
                    f"Stage {stage_name} is already finished, skipping it"
                )
                continue
            LOG.info(
                f"""Running {stage_name} stage
                Description: {stage['description']}
                IMPACT: {stage['impact']}
            """
            )
            state_cm.update(stage_name, STARTED)
            stage["executable"](script_args)
            state_cm.update(stage_name, COMPLETED)
            LOG.info(f"Completed {stage_name} stage")
        except Exception as e:
            error = e
            state_cm.update(stage_name, FAILED, error=traceback.format_exc())
            LOG.exception(f"Failed to run stage {stage_name}")
        finally:
            current_index = WORKFLOW.index(stage)
            if script_args.interactive and current_index != len(WORKFLOW) - 1:
                next_stage = WORKFLOW[current_index + 1]
                LOG.info(
                    f"""Next stage to run is {next_stage['name']}
                        Description: {next_stage['description']}
                        IMPACT: {next_stage['impact']}
                    """
                )
                msg = "To proceed to next stage press Y, to abort WHOLE procedure press N"
                res = check_input(lambda x: x in ["Y", "N"], msg)
                if res == "Y":
                    # Ignoring any errors if user chose to proceed
                    error = None
                elif res == "N":
                    LOG.warning("Aborting execution")
                    break
            if error:
                raise error


def do_preflight_checks():
    pass


def do_neutron_db_backup():
    pass


def main():
    args = set_args()
    if args.mode == "migration":
        do_migration(args)
    elif args.mode == "preflight_checks":
        do_preflight_checks()
    elif args.mode == "backup_db":
        do_neutron_db_backup()


if __name__ == "__main__":
    main()
