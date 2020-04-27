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
```
kubectl label node -l node-role.kubernetes.io/master!= openstack-control-plane=enabled openstack-compute-node=enabled openvswitch=enabled role=ceph-osd-node
```

## Usage

### Download release-openstack-k8s repo
```
git clone "https://gerrit.mcp.mirantis.com/mcp/release-openstack-k8s"
cd release-openstack-k8s
git tag -n
git checkout 0.1.10
```

### Deploy infra parts

These include required CRDs and controllers for Helm, Ceph and OpenStack.

Create resources one by one with small delay to ensure kopfpeering is created by ceph.
```
    for d in release 3rd-party ci; do
      pushd release
      for i in $(ls -1 ./*); do
        kubectl apply -f $i
        sleep 10
      done
      popd
    done
```

### Deploy ceph cluster
1. Update node names in examples/miraceph/ceph_local_folder_openstack.yaml
2. Deploy Ceph cluster
```
kubectl apply -f examples/miraceph/ceph_local_folder_openstack.yaml
```

### Deploy OpenStack

#### Update DNS

to match currently configured in the Kubernetes cluster

```
sed -i "s/kaas-kubernetes-3af5ae538cf411e9a6c7fa163e5a4837/$(kubectl get configmap -n kube-system coredns -o jsonpath='{.data.Corefile}' |grep -oh kaas-kubernetes-[[:alnum:]]*)/g" examples/osdpl/core-ceph-local-non-dvr.yaml
```

#### Generate Certs for public endpoints

Generate certs with correct domain
```
relase_repo_path=~/release-openstack-k8s
pushd openstack-controller/tools/ssl
  bash/makecerts.sh $relase_repo_path/examples/osdpl/core-ceph-local-non-dvr.yaml
popd
```

#### Create OpenStackDeployment
```
relase_repo_path=~/release-openstack-k8s
kubectl apply -f $relase_repo_path/examples/osdpl/core-ceph-local-non-dvr.yaml
```

## Validate OpenStack

Access the keystone-client pod
```
kubectl -n openstack get pods -l application=keystone,compoment=client
# example output
# NAME                               READY   STATUS    RESTARTS   AGE
# keystone-client-84d5f99754-7tdz6   1/1     Running   0          14d

kubectl -n openstack exec -it keystone-client-84d5f99754-7tdz6 -- bash
```

Inside the pod you have openstack client with mounted keystone admin credentials,
so for example you can do:
```
wget https://binary.mirantis.com/openstack/bin/cirros/0.5.1/cirros-0.5.1-x86_64-disk.img
openstack image create cirros-0.5.1-x86_64-disk --file cirros-0.5.1-x86_64-disk.img --disk-format qcow2 --container-format bare --public
openstack network create demoNetwork
openstack subnet create demoSubnet --network demoNetwork --subnet-range 10.11.12.0/24
openstack server create --image cirros-0.5.1-x86_64-disk --flavor m1.tiny --nic net-id=demoNetwork DemoVM
```

## Advanced Usage

### Connect to helm directly

```
# Download helm client with your version:
wget https://get.helm.sh/helm-v2.13.1-linux-amd64.tar.gz
tar -xf helm-v2.13.1-linux-amd64.tar.gz
mv linux-amd64/helm /usr/local/bin/helm

# Setup port forwarding to tiller service
kubectl port-forward -n osh-system helm-controller-0 44134:44134

# Setup alias for bash command, or add `--host=localhost:44134` to each command
alias helm="helm --host=localhost:44134"

# Init helm
helm init

# Use helm as always :)
helm list
```

# Admission Controller for Kubernetes OpenStackDeployment

You can read more about admission controllers [here](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers).
To use this particular admission controller, you need to have
ValidatingAdmissionWebhook admission plugin enabled in Kubernetes API server.

Should be run under uwsgi, for example:

`$ uwsgi uwsgi.ini`

As the service runs under HTTPS, you need to also provide server certificate
and key (named oac.crt and oac.key) by default. They can be generated for
example by using [this script](https://github.com/alex-leonhardt/k8s-mutate-webhook/blob/master/ssl/ssl.sh).
