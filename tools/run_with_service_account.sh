#!/bin/bash
set -e
set -o pipefail

source tools/get_service_account.sh
python3 tools/set-cluster-insecure.py $KUBECFG_FILE_NAME
echo using kube config file $KUBECFG_FILE_NAME
export KUBECONFIG=$KUBECFG_FILE_NAME
HELM_BINARY="https://binary.mirantis.com/openstack/bin/utils/helm/helm-v3.6.2-linux-amd64"

export NODE_IP=${NODE_IP:$(ip route get 4.2.2.1 | awk '{print $7}' | head -1)}
export OS_CLIENT_CONFIG_FILE="/tmp/osctl-clouds.yaml"

if ! which helm3; then
    wget -O /usr/bin/helm3 $HELM_BINARY
    chmod +x /usr/bin/helm3
fi

. tools/fill_internal_svc_ips.sh

available_controllers=(
    "-m openstack_controller.controllers.node"
    "-m openstack_controller.controllers.openstackdeployment"
    "-m openstack_controller.controllers.secrets"
    "-m openstack_controller.controllers.health"
    "-m openstack_controller.controllers.probe"
    "-m openstack_controller.controllers.maintenance"
    "-m openstack_controller.controllers.openstackdeploymentstatus"
    "-m openstack_controller.controllers.openstackdeploymentsecret"
)

controllers="${available_controllers[*]}"

kopf run --dev -n openstack -P openstack-controller.osdpl --liveness=http://:8090/healthz $controllers
