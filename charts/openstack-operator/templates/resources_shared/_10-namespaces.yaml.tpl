---
apiVersion: v1
kind: Namespace
metadata:
  name: osh-system
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.helmbundle.enabled }}"create"{{ else }}"wait"{{ end }}
---
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .Values.tf.sharedNamespace }}
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.tf.createSharedNamespace }}"create"{{ else }}"wait"{{ end }}
---
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .Values.stacklight.sharedNamespace }}
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.stacklight.createSharedNamespace }}"create"{{ else }}"wait"{{ end }}
---
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .Values.osdpl.settings.raw.OSCTL_REDIS_NAMESPACE }}
# NOTE(vsaienko): create shared namespace to make sure roles and
# rolebindings can be created succesfully. The kopfpeerings and
# shared namespace will be created by ceph operator by default.
---
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .Values.osdpl.cephSharedNamespace }}
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.kopf.enabled }}"create"{{ else }}"wait"{{ end }}
---
apiVersion: v1
kind: Namespace
metadata:
  name: {{ .Values.osdpl.namespace }}
