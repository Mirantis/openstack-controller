# osh-operator

Operator to deploy **O**pen**S**tack-**H**elm charts onto KaaS

## Prerequisites

Working kubernetes cluster with multiple computes where node labeling is done according to theirs roles.

For openstack we will require the following labels:

 * ``openstack-control-plane=enabled`` - for k8s computes that will host openstack control plane containers
 * ``openstack-compute-node=enabled`` - for k8s computes that will host openstack compute nodes
 * ``openvswitch=enabled`` - for k8s computes that will host openstack network gateway services and compute nodes

For ceph we will require the following labels:

 * ``role=ceph-osd-node`` - for k8s computes that will host ceph osd's

## Usage

### Deploy osh-operator (crds, operator, helmbundlecontroller)

`kubectl apply -f crds/`

Deploy Ceph (Optional)

Deploy Rook

`kubectl apply -f https://raw.githubusercontent.com/jumpojoy/os-k8s/master/crds/helmbundle/ceph/rook.yaml`

Deploy ceph cluster

`kubectl apply -f https://raw.githubusercontent.com/jumpojoy/os-k8s/master/crds/ceph/cluster.yaml`

Create storageclass

`kubectl apply -f https://raw.githubusercontent.com/jumpojoy/os-k8s/master/crds/ceph/storageclass.yaml`

Share metadata with openstack

`kubectl get secret rook-ceph-admin-keyring -n rook-ceph --export -o yaml | sed -e 's/keyring:/key:/' | kubectl apply -n default -f-`
`kubectl cp rook-ceph/$(kubectl -n rook-ceph get pod -l "app=rook-ceph-operator" -o jsonpath='{.items[0].metadata.name}'):/etc/ceph/ceph.conf /tmp/ceph.conf && sed -i 's/[a-z]1\+://g' /tmp/ceph.conf; sed -i '/^\[client.admin\]/d' /tmp/ceph.conf; sed -i '/^keyring =/d' /tmp/ceph.conf; sed -i '/^$/d' /tmp/ceph.conf; kubectl create configmap rook-ceph-config -n default --from-file=/tmp/ceph.conf`

### Deploy OpenStack

Update DNS to match currently configured by kaas

`sed -i "s/kaas-kubernetes-3af5ae538cf411e9a6c7fa163e5a4837/$(kubectl get configmap -n kube-system coredns -o jsonpath='{.data.Corefile}' |grep -oh kaas-kubernetes-[[:alnum:]]*)/g" examples/stein/core-ceph.yaml`

`kubectl apply -f examples/stein/core-ceph.yaml`

### Post deployment hacks

Update host OS dns to point to kubernetes coredns

`sed -i 's/#DNS=/DNS=10.233.0.3/g' /etc/systemd/resolved.conf`
`systemctl restart systemd-resolved`
