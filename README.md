# osh-operator

Operator to deploy **O**pen**S**tack-**H**elm charts onto KaaS

## Prerequisites

Working kubernetes cluster with multiple computes where node labeling is done according to theirs roles.

For openstack we will require the following labels:

 * `openstack-control-plane=enabled` - for k8s computes that will host openstack control plane containers
 * `openstack-compute-node=enabled` - for k8s computes that will host openstack compute nodes
 * `openvswitch=enabled` - for k8s computes that will host openstack network gateway services and compute nodes

For ceph we will require the following labels:

 * `role=ceph-osd-node` - for k8s computes that will host ceph osd's

Apply all the required labels to all the nodes except of master k8s node
(**only for dev envs!**):

 * `kubectl label node -l node-role.kubernetes.io/master!= openstack-control-plane=enabled openstack-compute-node=enabled openvswitch=enabled role=ceph-osd-node`

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

`kubectl get secret rook-ceph-admin-keyring -n rook-ceph --export -o yaml | sed -e 's/keyring:/key:/' | kubectl apply -n openstack -f-`
`kubectl cp rook-ceph/$(kubectl -n rook-ceph get pod -l "app=rook-ceph-operator" -o jsonpath='{.items[0].metadata.name}'):/etc/ceph/ceph.conf /tmp/ceph.conf && sed -i 's/[a-z]1\+://g' /tmp/ceph.conf; sed -i '/^\[client.admin\]/d' /tmp/ceph.conf; sed -i '/^keyring =/d' /tmp/ceph.conf; sed -i '/^$/d' /tmp/ceph.conf; kubectl create configmap rook-ceph-config -n openstack --from-file=/tmp/ceph.conf`

### Deploy OpenStack

Update DNS to match currently configured by kaas

`sed -i "s/kaas-kubernetes-3af5ae538cf411e9a6c7fa163e5a4837/$(kubectl get configmap -n kube-system coredns -o jsonpath='{.data.Corefile}' |grep -oh kaas-kubernetes-[[:alnum:]]*)/g" examples/stein/core-ceph.yaml`

`kubectl apply -f examples/stein/core-ceph.yaml`

### Post deployment hacks

Update host OS dns to point to kubernetes coredns

`sed -i 's/#DNS=/DNS=10.233.0.3/g' /etc/systemd/resolved.conf`
`systemctl restart systemd-resolved`

## Validate OpenStack

```
mkdir /etc/openstack
tee /etc/openstack/clouds.yaml << EOF
clouds:
  openstack_helm:
    region_name: RegionOne
    identity_api_version: 3
    auth:
      username: 'admin'
      password: 'password'
      project_name: 'admin'
      project_domain_name: 'default'
      user_domain_name: 'default'
      auth_url: 'http://keystone.openstack.svc.$(kubectl get configmap -n kube-system coredns -o jsonpath='{.data.Corefile}' |grep -oh kaas-kubernetes-[[:alnum:]]*)/v3'
EOF

export OS_CLOUD=openstack_helm

apt-get install virtualenv build-essential python-dev
virtualenv osclient
source osclient/bin/activate
pip install python-openstackclient

wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img
openstack image create cirros-0.4.0-x86_64-disk --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --container-format bare
openstack network create demoNetwork
openstack subnet create demoSubnet --network demoNetwork --subnet-range 10.11.12.0/24
openstack server create --image cirros-0.4.0-x86_64-disk --flavor m1.tiny --nic net-id=demoNetwork DemoVM
```
