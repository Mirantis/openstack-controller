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

### Create shared namespace with ceph secrets

`kubectl crate ns ceph-lcm-mirantis`

### Deploy osh-operator (crds, operator, helmbundlecontroller)

`kubectl apply -f crds/`

Deploy Ceph (Optional)

Deploy Rook

`kubectl apply -f https://raw.githubusercontent.com/jumpojoy/os-k8s/master/crds/helmbundle/ceph/rook.yaml`

Deploy ceph cluster

`kubectl apply -f https://raw.githubusercontent.com/jumpojoy/os-k8s/master/crds/ceph/cluster.yaml`

Create Ceph storageclass

`kubectl apply -f https://raw.githubusercontent.com/jumpojoy/os-k8s/master/crds/ceph/storageclass.yaml`

Share metadata with openstack

`kubectl -n rook-ceph get secret rook-ceph-admin-keyring -o yaml  --export | kubectl apply -n ceph-lcm-mirantis -f-`
`kubectl -n rook-ceph get configmaps rook-ceph-mon-endpoints -o yaml --export | kubectl apply -n ceph-lcm-mirantis -f-`


In case local volumes are used for Mariadb and/or Rabbitmq configure local volumes provisioner as follows.
Setup mount points for local volumes provisioner (1 mount point - 1 volume) (Workaround for https://mirantis.jira.com/browse/PROD-31627)

```
nodeVolumesCount=3
volDirPrefix='vol'
sshUser='ubuntu'
for node in $(sudo kubectl --kubeconfig=/root/.kube/config get nodes -o NAME -l openstack-control-plane=enabled); do
  ip=$(sudo kubectl --kubeconfig=/root/.kube/config describe ${node} | grep InternalIP | cut -d' ' -f5;)
  for i in $(seq 1 $nodeVolumesCount); do
    volDir="${volDirPrefix}-${i}"
    ssh -o "StrictHostKeyChecking=no" ${sshUser}@${ip} "sudo mkdir -p /mnt/local-provisioner/${volDir} && sudo mkdir -p /mnt/${volDir}"
    ssh -o "StrictHostKeyChecking=no" ${sshUser}@${ip} "sudo mount --bind /mnt/${volDir} /mnt/local-provisioner/${volDir}"
    ssh -o "StrictHostKeyChecking=no" ${sshUser}@${ip} "echo '/mnt/${volDir} /mnt/local-provisioner/${volDir} none defaults,bind 0 0' | sudo tee -a /etc/fstab"
  done;
done;
```

Setup provisioner for local volumes and related storage class (workaround for https://mirantis.jira.com/browse/PROD-31681)

`git clone https://<username>@gerrit.mcp.mirantis.com/a/mcp/mcp-pipelines.git`
kubectl apply -f mcp-pipelines/tools/openstack-local-volume-provisoner.yaml


### Deploy OpenStack

Update DNS to match currently configured by kaas

`sed -i "s/kaas-kubernetes-3af5ae538cf411e9a6c7fa163e5a4837/$(kubectl get configmap -n kube-system coredns -o jsonpath='{.data.Corefile}' |grep -oh kaas-kubernetes-[[:alnum:]]*)/g" examples/stein/core-ceph.yaml`

`kubectl apply -f examples/stein/core-ceph.yaml`

### Post deployment hacks

Update host OS dns to point to kubernetes coredns

`sed -i "s/#DNS=/DNS=$(kubectl get svc coredns -n kube-system -ojsonpath='{.spec.clusterIP}')/g" /etc/systemd/resolved.conf`
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
      username: '$(kubectl -n openstack get secrets keystone-keystone-admin -o jsonpath='{.data.OS_USERNAME}' | base64 -d)'
      password: '$(kubectl -n openstack get secrets keystone-keystone-admin -o jsonpath='{.data.OS_PASSWORD}' | base64 -d)'
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
openstack image create cirros-0.4.0-x86_64-disk --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --container-format bare --public
openstack network create demoNetwork
openstack subnet create demoSubnet --network demoNetwork --subnet-range 10.11.12.0/24
openstack server create --image cirros-0.4.0-x86_64-disk --flavor m1.tiny --nic net-id=demoNetwork DemoVM
```

## Advanced Usage

### Connect to helm directly

 - Download helm client with your version:
   wget https://get.helm.sh/helm-v2.13.1-linux-amd64.tar.gz
   tar -xf helm-v2.13.1-linux-amd64.tar.gz
   mv linux-amd64/helm /usr/local/bin/helm
 - Setup port forwarding to tiller service
   kubectl port-forward -n osh-system helm-controller-0 44134:44134
 - Setup alias for bas command, or add `--host=localhost:44134` to each command
   alias helm="helm --host=localhost:44134"
 - Init helm
   helm init
 - Use helm as always :)
   helm list
