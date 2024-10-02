#!/bin/bash

set -ex

OPENSTACK_CONTROLLER_DIR=${OPENSTACK_CONTROLLER_DIR:-'/root/openstack-controller'}
INVENTORY_FILE=${INVENTORY_FILE:-"${OPENSTACK_CONTROLLER_DIR}/virtual_lab/ansible/inventory/single_node.yaml"}

apt update -y
DEBIAN_FRONTEND=noninteractive apt install -y python3-pip


pip3 install ansible git-review


ansible-galaxy collection install bodsch.core
ansible-galaxy collection install bodsch.scm
ansible-galaxy role install bodsch.k0s

cd ${OPENSTACK_CONTROLLER_DIR}/virtual_lab/ansible/

ansible-playbook -i  ${INVENTORY_FILE} k0s-install.yaml

mkdir -p /root/.kube; cp ${OPENSTACK_CONTROLLER_DIR}/virtual_lab/ansible/inventory/artifacts/k0s-kubeconfig.yml /root/.kube/config

ansible-playbook -i  ${INVENTORY_FILE} oc-install.yaml
