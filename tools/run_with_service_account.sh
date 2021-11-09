#!/bin/bash
set -e
set -o pipefail

source tools/get_service_account.sh
python3 tools/set-cluster-insecure.py $KUBECFG_FILE_NAME
echo using kube config file $KUBECFG_FILE_NAME
export KUBECONFIG=$KUBECFG_FILE_NAME

export NODE_IP=${NODE_IP:$(ip route get 4.2.2.1 | awk '{print $7}' | head -1)}

available_controllers=(
    "-m openstack_controller.controllers.node"
    "-m openstack_controller.controllers.openstackdeployment"
    "-m openstack_controller.controllers.secrets"
    "-m openstack_controller.controllers.health"
    "-m openstack_controller.controllers.probe"
    "-m openstack_controller.controllers.maintenance"
    "-m openstack_controller.controllers.openstackdeploymentstatus"
)

controllers="${available_controllers[*]}"

kopf run --dev -n openstack -P openstack-controller.osdpl --liveness=http://:8090/healthz $controllers
