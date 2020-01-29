# openstack-controller

Controller to deploy and manage OpenStack on Kubernetes

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

### Deploy openstack-controller (crds, operator, helmbundlecontroller)

Create resources one by one with small delay to ensure kopfpeering is created by ceph.
`pushd deploy/helmbundle; for i in $(ls -1 ./*); do kubectl apply -f $i; sleep 10 done; popd`

In case to deploy with Ceph (Optional)

Deploy ceph-kaas-controller to deploy Ceph related CRDs

Update node names in examples/ceph/ceph_local_folder_openstack.yaml

Deploy ceph cluster

`kubectl apply -f examples/ceph/ceph_local_folder_openstack.yaml`


### Deploy OpenStack

Update DNS to match currently configured by kaas

`sed -i "s/kaas-kubernetes-3af5ae538cf411e9a6c7fa163e5a4837/$(kubectl get configmap -n kube-system coredns -o jsonpath='{.data.Corefile}' |grep -oh kaas-kubernetes-[[:alnum:]]*)/g" examples/stein/core-ceph-local-non-dvr.yaml`

#### Generate Certs for public endpoints
Generate certs with correct domain
```
cd tools/ssl
./makecerts.sh
```
Add certificates to context:
```
spec:
  features:
    ssl:
      public_endpoints:
        api_cert: |
          server certificate content (from tools/ssl/certs/server.pem)
        api_key: |
          server private key content (from tools/ssl/certs/server-key.pem)
        ca_cert: |
          CA certificate content (from tools/ssl/certs/ca.pem)
```

`kubectl apply -f examples/stein/core-ceph.yaml`


## Validate OpenStack

```
kubect -n openstack exec -it keystone-client-8987f9985-h7c2l -- bash


wget https://binary.mirantis.com/openstack/bin/cirros/0.4.0/cirros-0.4.0-x86_64-disk.img
openstack image create cirros-0.4.0-x86_64-disk --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --container-format bare --public
openstack network create demoNetwork
openstack subnet create demoSubnet --network demoNetwork --subnet-range 10.11.12.0/24
openstack server create --image cirros-0.4.0-x86_64-disk --flavor m1.tiny --nic net-id=demoNetwork DemoVM
```
## Barbican installation
###Simple_crypto backend configuration
```
 barbican:
   backend:
     simple_crypto:
       enabled: True
       kek: 'YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY='
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

# Admission Controller for Kubernetes OpenStackDeployment

You can read more about admission controllers [here](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers).
To use this particular admission controller, you need to have
ValidatingAdmissionWebhook admission plugin enabled in Kubernetes API server.

Should be run under uwsgi, for example:

`$ uwsgi uwsgi.ini`

As the service runs under HTTPS, you need to also provide server certificate
and key (named oac.crt and oac.key) by default. They can be generated for
example by using [this script](https://github.com/alex-leonhardt/k8s-mutate-webhook/blob/master/ssl/ssl.sh).
