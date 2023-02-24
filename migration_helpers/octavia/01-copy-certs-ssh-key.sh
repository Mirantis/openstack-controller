#!/bin/bash -e
#
# THIS FILE IS GOING TO BE EXECUTED ON ANY CFG NODES (MCP1).
#
RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$(cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common

OCTAVIA_MGR_NODE=$(salt -C 'I@octavia:manager and *01*' grains.get fqdn --out newline_values_only)
CACHE_DIR="/var/cache/salt/master/minions/${OCTAVIA_MGR_NODE}/files/etc/octavia"
salt "${OCTAVIA_MGR_NODE}" cp.push_dir /etc/octavia
chmod 0600 "${CACHE_DIR}"/.ssh/octavia_ssh_key
public_key=$(ssh-keygen -f "${CACHE_DIR}"/.ssh/octavia_ssh_key -y)

kubectl delete secret octavia-certs -n openstack
kubectl create secret generic octavia-certs -n openstack --from-file=cert="${CACHE_DIR}"/certs/ca_01.pem --from-file=cert_all="${CACHE_DIR}"/certs/client_all.pem --from-file=key="${CACHE_DIR}"/certs/ca.key

kubectl delete secret amphora-ssh-key -n openstack
kubectl create secret generic amphora-ssh-key -n openstack --from-file=octavia_ssh_key="${CACHE_DIR}"/.ssh/octavia_ssh_key --from-literal=octavia_ssh_key_pub="${public_key}"
