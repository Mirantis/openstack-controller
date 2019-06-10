# osh-operator

Operator to deploy **O**pen**S**tack-**H**elm charts onto KaaS

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

`kubectl apply -f examples/stein/core-ceph.yaml`

## MicroK8S tips

https://microk8s.io/docs/

enable DNS and Registry support

`microk8s.enable dns registry`

if needed, add extra DNS to the kube-dns

`microk8s.kubectl -n kube-system edit configmap/kube-dns`

enable port forwarding on your machine

`sudo iptables -P FORWARD ACCEPT`

also see `microk8s.inspect`

build local image with docker

`docker build . -t localhost:32000/osh-operator:registry`

push it to the microk8s registry

`docker push localhost:32000/osh-operator`

redeploy the operator

`kubect delete -f deployment.yaml && kubectl apply -f deployment.yaml`
