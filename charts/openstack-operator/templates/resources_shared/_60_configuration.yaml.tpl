apiVersion: v1
data:
kind: ConfigMap
metadata:
  name: openstack-controller-config
  namespace: {{ .Release.Namespace }}
  annotations:
    # NOTE(vsaienko): do not update resource if exist to avoid config loose
    "openstackdeployments.lcm.mirantis.com/skip_update": "true"
