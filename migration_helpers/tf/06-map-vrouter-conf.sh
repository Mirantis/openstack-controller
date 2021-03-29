#!/bin/bash

set -e #x

RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$( cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common
. $TOP_DIR/database/functions

SALTFORMULA_DIR=${SALTFORMULA_DIR:-"/srv/salt/env/prd/"}

function get_ips {
  pod_names=$(kubectl -n tf get pod -l tungstenfabric=$1  -o name | cut -d/ -f 2)
  ips=""
  for p in $pod_names; do
    ips=${ips}"$(kubectl -n tf get pod $p --template={{.status.podIP}}):$2 ";
  done
  echo $ips
}

function map_vrouter_agents {
  local CONTROL=$(get_ips control "5269")
  local DNS=$(get_ips control "53")

  local CONFIG_FILENAME="${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-vrouter-agent.conf"
  echo "MANUAL ACTION REQUIRED"
  echo "Update $CONFIG_FILENAME set servers in section [DNS] to $DNS, in section [CONTROL-NODE] to $CONTROL"

}

map_vrouter_agents