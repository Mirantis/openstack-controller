#!/bin/bash
set -e
set -o pipefail

source tools/get_service_account.sh
python3 tools/set-cluster-insecure.py $KUBECFG_FILE_NAME
echo using kube config file $KUBECFG_FILE_NAME
export KUBECONFIG=$KUBECFG_FILE_NAME

available_controllers=(
    "-m openstack_controller.controllers.node"
    "-m openstack_controller.controllers.openstackdeployment"
    "-m openstack_controller.controllers.helmbundle"
    "-m openstack_controller.controllers.secrets"
    "-m openstack_controller.controllers.health"
    "-m openstack_controller.controllers.probe"
    "-m openstack_controller.controllers.node_maintenance_request"
)

controllers="${available_controllers[*]}"

kopf run --dev -n openstack -P openstack-controller.osdpl --liveness=http://:8090/healthz $controllers
