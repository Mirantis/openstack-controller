---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.node_maintenance.create_crd }}"create"{{ else }}"wait"{{ end }}
  name: clustermaintenancerequests.lcm.mirantis.com
spec:
  group: lcm.mirantis.com
  names:
    kind: ClusterMaintenanceRequest
    listKind: ClusterMaintenanceRequestList
    plural: clustermaintenancerequests
    singular: clustermaintenancerequest
  scope: Cluster
  versions:
  - name: v1alpha1
    schema:
      openAPIV3Schema:
        properties:
          apiVersion:
            description: 'APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources'
            type: string
          kind:
            description: 'Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds'
            type: string
          metadata:
            type: object
          spec:
            properties:
              scope:
                enum:
                - os
                - drain
                type: string
            type: object
        type: object
    served: true
    storage: true
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.node_maintenance.create_crd }}"create"{{ else }}"wait"{{ end }}
  name: clusterworkloadlocks.lcm.mirantis.com
spec:
  group: lcm.mirantis.com
  names:
    kind: ClusterWorkloadLock
    listKind: ClusterWorkloadLockList
    plural: clusterworkloadlocks
    singular: clusterworkloadlock
  scope: Cluster
  versions:
  - name: v1alpha1
    schema:
      openAPIV3Schema:
        properties:
          apiVersion:
            description: 'APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources'
            type: string
          kind:
            description: 'Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds'
            type: string
          metadata:
            type: object
          spec:
            properties:
              controllerName:
                type: string
            required:
            - controllerName
            type: object
          status:
            properties:
              errorMessage:
                type: string
              release:
                type: string
              state:
                default: active
                enum:
                - inactive
                - active
                - failed
                type: string
            required:
            - state
            type: object
        type: object
    served: true
    storage: true
    subresources:
      status: {}
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.node_maintenance.create_crd }}"create"{{ else }}"wait"{{ end }}
  name: nodemaintenancerequests.lcm.mirantis.com
spec:
  group: lcm.mirantis.com
  names:
    kind: NodeMaintenanceRequest
    listKind: NodeMaintenanceRequestList
    plural: nodemaintenancerequests
    singular: nodemaintenancerequest
  scope: Cluster
  versions:
  - name: v1alpha1
    schema:
      openAPIV3Schema:
        properties:
          apiVersion:
            description: 'APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources'
            type: string
          kind:
            description: 'Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds'
            type: string
          metadata:
            type: object
          spec:
            properties:
              nodeName:
                type: string
              scope:
                enum:
                - os
                - drain
                type: string
            required:
            - nodeName
            - scope
            type: object
        type: object
    served: true
    storage: true
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.node_maintenance.create_crd }}"create"{{ else }}"wait"{{ end }}
  name: nodeworkloadlocks.lcm.mirantis.com
spec:
  group: lcm.mirantis.com
  names:
    kind: NodeWorkloadLock
    listKind: NodeWorkloadLockList
    plural: nodeworkloadlocks
    singular: nodeworkloadlock
  scope: Cluster
  versions:
  - name: v1alpha1
    schema:
      openAPIV3Schema:
        properties:
          apiVersion:
            description: 'APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources'
            type: string
          kind:
            description: 'Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds'
            type: string
          metadata:
            type: object
          spec:
            properties:
              controllerName:
                type: string
              nodeName:
                type: string
            required:
            - controllerName
            - nodeName
            type: object
          status:
            properties:
              errorMessage:
                type: string
              release:
                type: string
              state:
                default: active
                enum:
                - inactive
                - active
                - failed
                type: string
            required:
            - state
            type: object
        type: object
    served: true
    storage: true
    subresources:
      status: {}
---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  annotations:
    "openstackdeployments.lcm.mirantis.com/shared_resource_action": {{ if .Values.node_maintenance.create_crd }}"create"{{ else }}"wait"{{ end }}
  name: nodedisablenotifications.lcm.mirantis.com
spec:
  group: lcm.mirantis.com
  names:
    kind: NodeDisableNotification
    listKind: NodeDisableNotificationList
    plural: nodedisablenotifications
    singular: nodedisablenotification
  preserveUnknownFields: false
  scope: Cluster
  versions:
  - name: v1alpha1
    schema:
      openAPIV3Schema:
        properties:
          apiVersion:
            description: 'APIVersion defines the versioned schema of this representation
              of an object. Servers should convert recognized schemas to the latest
              internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources'
            type: string
          kind:
            description: 'Kind is a string value representing the REST resource this
              object represents. Servers may infer this from the endpoint the client
              submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds'
            type: string
          metadata:
            type: object
          spec:
            properties:
              nodeName:
                type: string
            required:
            - nodeName
            type: object
        type: object
    served: true
    storage: true
