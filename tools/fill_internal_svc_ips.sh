#!/bin/bash
set -e
set -o pipefail

SERVICES="cinder-api keystone-api glance-api nova-api neutron-server barbican-api designate-api octavia-api placement-api"

HOSTS_FILE_IDENTIFIER="# Automatically set IP"

function get_svc_cluster_ip {
    local service=$1
    svc_ip=$(kubectl -n openstack get svc $service -o jsonpath='{.spec.clusterIP}')
    echo $svc_ip
}

sed -i "/${HOSTS_FILE_IDENTIFIER}/d" /etc/hosts

for service in $SERVICES; do
    svc_ip=$(get_svc_cluster_ip $service)
    echo "$service: $svc_ip"
    echo "$svc_ip ${service}.openstack.svc.cluster.local  $HOSTS_FILE_IDENTIFIER" >> /etc/hosts
done

