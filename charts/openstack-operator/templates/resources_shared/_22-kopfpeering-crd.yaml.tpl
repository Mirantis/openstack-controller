---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: clusterkopfpeerings.zalando.org
  annotations:
    "helm.sh/hook": crd-install
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.kopf.enabled }}"create"{{ else }}"wait"{{ end }}
spec:
  scope: Cluster
  group: zalando.org
  versions:
    - name: v1
      served: true
      storage: true
  names:
    kind: ClusterKopfPeering
    plural: clusterkopfpeerings
    singular: clusterkopfpeering
---
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: kopfpeerings.zalando.org
  annotations:
    "helm.sh/hook": crd-install
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.kopf.enabled }}"create"{{ else }}"wait"{{ end }}
spec:
  scope: Namespaced
  group: zalando.org
  versions:
    - name: v1
      served: true
      storage: true
  names:
    kind: KopfPeering
    plural: kopfpeerings
    singular: kopfpeering
