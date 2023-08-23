#!/bin/bash
set -e
set -o pipefail

OS_CLIENT_CONFIG_FILE=${OS_CLIENT_CONFIG_FILE:-/tmp/clouds_functional.yaml}

kubectl -n openstack-external get secrets openstack-identity-credentials -o jsonpath='{.data.clouds\.yaml}'  | base64 -d > ${OS_CLIENT_CONFIG_FILE}
sed -i 's/    endpoint_type: public/    endpoint_type: public\n    insecure: True/g' ${OS_CLIENT_CONFIG_FILE}

mkdir -p /etc/openstack-controller/exporter
kubectl -n osh-system get secrets openstack-controller-exporter-etc -o jsonpath='{.data.certs_info\.yaml}' | base64 -d > /etc/openstack-controller/exporter/certs_info.yaml
