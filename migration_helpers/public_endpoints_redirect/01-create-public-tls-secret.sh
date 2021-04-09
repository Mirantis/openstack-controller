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
  ca.crt: $(salt 'prx01*' pillar.items _param:apache_horizon_ssl:cert --out json | jq -r '.[][]' | base64 | tr -d '\n')
  tls.crt: $(salt 'prx01*' pillar.items _param:apache_horizon_ssl:chain --out json | jq -r '.[][]' | base64 | tr -d '\n')
  tls.key: $(salt 'prx01*' pillar.items _param:apache_horizon_ssl:key --out json | jq -r '.[][]' | base64 | tr -d '\n')
kind: Secret
metadata:
  annotations:
  name: public-endpoints-tls
  namespace: ${FORWARDER_NS}
type: tls
EOF

