---
apiVersion: zalando.org/v1
kind: ClusterKopfPeering
metadata:
  name: openstack-controller
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.namespace }}"
  name: openstack-controller.osdpl
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.namespace }}"
  name: openstack-controller.osdplstatus
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.namespace }}"
  name: openstack-controller.secrets
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.namespace }}"
  name: openstack-controller.health
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.namespace }}"
  name: openstack-controller.node
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.namespace }}"
  name: openstack-controller.nodemaintenancerequest
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.cephSharedNamespace }}"
  name: openstack-controller.ceph.secrets
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.osdpl.namespace }}"
  name: openstack-controller.osdplsecret
---
apiVersion: zalando.org/v1
kind: KopfPeering
metadata:
  namespace: "{{ .Values.tf.sharedNamespace }}"
  name: openstack-controller.tf.secrets
