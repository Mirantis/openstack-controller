{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "openstack-controller.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "openstack-controller.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "openstack-controller.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Generate full image paths for KaaS CDN
*/}}
{{- define "getImageUrl" -}}
{{- $context := index . 0 -}}
{{- $imageContext := index . 1 -}}
{{- if ($imageContext.fullName) -}}
{{- $imageContext.fullName -}}
{{- else -}}
{{- printf "%s/%s/%s:%s" $context.Values.global.dockerBaseUrl $imageContext.repository $imageContext.name $imageContext.tag -}}
{{- end -}}
{{- end -}}

{{- define "template" -}}
{{- $name := index . 0 -}}
{{- $context := index . 1 -}}
{{- $last := base $context.Template.Name }}
{{- $wtf := $context.Template.Name | replace $last $name -}}
{{ include $wtf $context }}
{{- end -}}

{{/*
Generate environment variables for osdpl containers
*/}}
{{- define "openstack-controller.common_env" }}
{{- $context := index . 0 -}}
- name: OSCTL_PROXY_SECRET_NAMESPACE
  value: {{ index $context.Values.global.proxy "namespace" | default $context.Values.osdpl.namespace }}
- name: OSCTL_OS_DEPLOYMENT_NAMESPACE
  value: {{ $context.Values.osdpl.namespace }}
- name: OSCTL_CEPH_SHARED_NAMESPACE
  value: {{ $context.Values.osdpl.cephSharedNamespace }}
- name: OSCTL_IMAGES_BASE_URL
  value: {{ $context.Values.global.dockerBaseUrl }}
- name: OSCTL_BINARY_BASE_URL
  value: {{ $context.Values.global.helmBaseUrl }}
- name: NODE_IP
  valueFrom:
    fieldRef:
      fieldPath: status.hostIP
- name: OSCTL_NODE_MAINTENANCE_ENABLED
  value: {{ $context.Values.node_maintenance.enabled | quote }}
  {{- if index $context.Values.global "clusterRelease"  }}
- name: OSCTL_CLUSTER_RELEASE
  value: {{ $context.Values.global.clusterRelease }}
  {{- end }}
{{- end }}

{{/*
Generate hash for resource.
*/}}
{{- define "opentsack-controller.utils.hash" -}}
{{- $name := index . 0 -}}
{{- $context := index . 1 -}}
{{- $last := base $context.Template.Name }}
{{- $wtf := $context.Template.Name | replace $last $name -}}
{{- include $wtf $context | sha256sum | quote -}}
{{- end -}}
