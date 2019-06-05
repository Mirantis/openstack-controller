# koshkaas

**K**opf-based operator to deploy **O**pen**S**tack-**H**elm charts onto **KaaS**.

## Example

deploy CustomResourceDefinition

`kubectl apply -f crd.yaml`

configure RBAC

`kubectl apply -f rbac.yaml`

deploy operator

`kubectl apply -f deployment.yaml`

instantiate custom resource

`kubeclt apply -f res.yaml`
