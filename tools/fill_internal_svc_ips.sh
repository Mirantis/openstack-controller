#!/bin/bash
set -e
set -o pipefail

SERVICES="cinder-api keystone-api glance-api nova-api neutron-server barbican-api designate-api octavia-api placement-api masakari-api heat-api"

HOSTS_FILE_IDENTIFIER="# Automatically set IP"

function get_svc_cluster_ip {
    local service=$1
    local namespace="${2:-openstack}"
    svc_ip=$(kubectl -n ${namespace} get svc $service -o jsonpath='{.spec.clusterIP}')
    echo $svc_ip
}

sed -i "/${HOSTS_FILE_IDENTIFIER}/d" /etc/hosts

for service in $SERVICES; do
    svc_ip=$(get_svc_cluster_ip $service)
    echo "$service: $svc_ip"
    echo "$svc_ip ${service}.openstack.svc.cluster.local  $HOSTS_FILE_IDENTIFIER" >> /etc/hosts
done

svc_ip=$(get_svc_cluster_ip openstack-controller-exporter osh-system)
echo "openstack-controller-exporter: $svc_ip"
echo "$svc_ip openstack-controller-exporter.osh-system.svc.cluster.local  $HOSTS_FILE_IDENTIFIER" >> /etc/hosts

svc_ip=$(get_svc_cluster_ip grafana stacklight)
echo "grafana: $svc_ip"
echo "$svc_ip grafana.stacklight $HOSTS_FILE_IDENTIFIER" >> /etc/hosts

# Set public IPs
ingress_ip=$(kubectl -n openstack get svc ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
for host in $(kubectl -n openstack get ingress | awk '/it.just.works/ {print $3}'); do
     echo "$ingress_ip $host" >> /etc/hosts
done
