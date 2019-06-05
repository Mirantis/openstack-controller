# osh-operator

Operator to deploy **O**pen**S**tack-**H**elm charts onto KaaS

## Example

deploy CustomResourceDefinition

`kubectl apply -f crd.yaml`

configure RBAC

`kubectl apply -f rbac.yaml`

deploy operator

`kubectl apply -f deployment.yaml`

instantiate custom resource

`kubeclt apply -f res.yaml`

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
