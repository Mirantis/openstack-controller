#!/bin/bash

RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$(cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common
. $TOP_DIR/database/functions

kubectl create ns ${HELMBUNDLE_NS}

cat << EOF | kubectl apply -f -
apiVersion: v1
data:
  ca.crt: $(kubectl get osdpl osh-dev -n openstack -o jsonpath='{.spec.features.ssl.public_endpoints.ca_cert}' | base64 | tr -d '\n')
  tls.crt: $(kubectl get osdpl osh-dev -n openstack -o jsonpath='{.spec.features.ssl.public_endpoints.api_cert}{"\n"}{.spec.features.ssl.public_endpoints.ca_cert}' | base64 | tr -d '\n')
  tls.key: $(kubectl get osdpl osh-dev -n openstack -o jsonpath='{.spec.features.ssl.public_endpoints.api_key}' | base64 | tr -d '\n')
kind: Secret
metadata:
  annotations:
  name: public-endpoints-tls
  namespace: ${FORWARDER_NS}
type: tls
EOF

