#!/bin/bash

set -e #x

RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$( cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common
. $TOP_DIR/database/functions

SALTFORMULA_DIR=${SALTFORMULA_DIR:-"/srv/salt/env/prd/"}


function get_analytics {
  pod_names=$(kubectl -n tf get pod -l tungstenfabric=analytics  -o name | cut -d/ -f 2)
  ips=""
  for p in $pod_names; do
    ips=${ips}"$(kubectl -n tf get pod $p --template={{.status.podIP}}):$1 ";
  done
  echo $ips
}


function switch_analytics {

CONF_LIST_1=\
"${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-alarm-gen.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-analytics-api.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-api.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-control.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-device-manager.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-dns.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-query-engine.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-schema.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-snmp-collector.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-svc-monitor.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-topology.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-vrouter-agent.conf"

CONF_LIST_2=\
"${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-analytics-nodemgr.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-config-nodemgr.conf
${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-control-nodemgr.conf"

local COLLECTORS=$(get_analytics "8086")
VAR="collectors"
for i in ${CONF_LIST_1}; do
  echo "Updating collectors in $i"
  sed -i  "s/\($VAR *= *\).*/\1${COLLECTORS}/" ${i};
done

VAR="server_list"
for i in ${CONF_LIST_2}; do
  echo "Updating collectors in $i"
  sed -i  "s/\($VAR *= *\).*/\1${COLLECTORS}/" ${i};
done

local API=$(get_analytics "8081")

VAR="analytics_server_list"
echo "Update analytics API"
sed -i  "s/\($VAR *= *\).*/\1${API}/" "${SALTFORMULA_DIR}opencontrail/files/4.1/contrail-svc-monitor.conf";
}

switch_analytics

refresh_pillars
info "Update opencontrail config files"
salt -C 'ntw*' state.sls opencontrail.config
salt -C 'ntw*' state.sls opencontrail.control
salt -C 'nal*' state.sls opencontrail.collector
salt -C 'cmp*' state.sls opencontrail.compute

info "Update hosts and recreate opencontrail docker containers"
salt -C 'ntw* or nal*' state.sls linux.network.host
salt -C 'ntw* or nal*' state.sls docker