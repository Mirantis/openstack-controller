---
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  annotations:
    controller-gen.kubebuilder.io/version: (devel)
  creationTimestamp: null
  name: redisfailovers.databases.spotahome.com
spec:
  group: databases.spotahome.com
  names:
    kind: RedisFailover
    listKind: RedisFailoverList
    plural: redisfailovers
    shortNames:
    - rf
    singular: redisfailover
  scope: Namespaced
  versions:
  - additionalPrinterColumns:
    - jsonPath: .metadata.name
      name: NAME
      type: string
    - jsonPath: .spec.redis.replicas
      name: REDIS
      type: integer
    - jsonPath: .spec.sentinel.replicas
      name: SENTINELS
      type: integer
    - jsonPath: .metadata.creationTimestamp
      name: AGE
      type: date
    name: v1
    schema:
      openAPIV3Schema:
        description: RedisFailover represents a Redis failover
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
            description: RedisFailoverSpec represents a Redis failover spec
            properties:
              auth:
                description: AuthSettings contains settings about auth
                properties:
                  secretPath:
                    type: string
                type: object
              bootstrapNode:
                description: BootstrapSettings contains settings about a potential
                  bootstrap node
                properties:
                  allowSentinels:
                    type: boolean
                  host:
                    type: string
                  port:
                    type: string
                type: object
              labelWhitelist:
                items:
                  type: string
                type: array
              redis:
                description: RedisSettings defines the specification of the redis
                  cluster
                properties:
                  affinity:
                    description: Affinity is a group of affinity scheduling rules.
                    properties:
                      nodeAffinity:
                        description: Describes node affinity scheduling rules for
                          the pod.
                        properties:
                          preferredDuringSchedulingIgnoredDuringExecution:
                            description: The scheduler will prefer to schedule pods
                              to nodes that satisfy the affinity expressions specified
                              by this field, but it may choose a node that violates
                              one or more of the expressions. The node that is most
                              preferred is the one with the greatest sum of weights,
                              i.e. for each node that meets all of the scheduling
                              requirements (resource request, requiredDuringScheduling
                              affinity expressions, etc.), compute a sum by iterating
                              through the elements of this field and adding "weight"
                              to the sum if the node matches the corresponding matchExpressions;
                              the node(s) with the highest sum are the most preferred.
                            items:
                              description: An empty preferred scheduling term matches
                                all objects with implicit weight 0 (i.e. it's a no-op).
                                A null preferred scheduling term matches no objects
                                (i.e. is also a no-op).
                              properties:
                                preference:
                                  description: A node selector term, associated with
                                    the corresponding weight.
                                  properties:
                                    matchExpressions:
                                      description: A list of node selector requirements
                                        by node's labels.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchFields:
                                      description: A list of node selector requirements
                                        by node's fields.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                  type: object
                                weight:
                                  description: Weight associated with matching the
                                    corresponding nodeSelectorTerm, in the range 1-100.
                                  format: int32
                                  type: integer
                              required:
                              - preference
                              - weight
                              type: object
                            type: array
                          requiredDuringSchedulingIgnoredDuringExecution:
                            description: If the affinity requirements specified by
                              this field are not met at scheduling time, the pod will
                              not be scheduled onto the node. If the affinity requirements
                              specified by this field cease to be met at some point
                              during pod execution (e.g. due to an update), the system
                              may or may not try to eventually evict the pod from
                              its node.
                            properties:
                              nodeSelectorTerms:
                                description: Required. A list of node selector terms.
                                  The terms are ORed.
                                items:
                                  description: A null or empty node selector term
                                    matches no objects. The requirements of them are
                                    ANDed. The TopologySelectorTerm type implements
                                    a subset of the NodeSelectorTerm.
                                  properties:
                                    matchExpressions:
                                      description: A list of node selector requirements
                                        by node's labels.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchFields:
                                      description: A list of node selector requirements
                                        by node's fields.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                  type: object
                                type: array
                            required:
                            - nodeSelectorTerms
                            type: object
                        type: object
                      podAffinity:
                        description: Describes pod affinity scheduling rules (e.g.
                          co-locate this pod in the same node, zone, etc. as some
                          other pod(s)).
                        properties:
                          preferredDuringSchedulingIgnoredDuringExecution:
                            description: The scheduler will prefer to schedule pods
                              to nodes that satisfy the affinity expressions specified
                              by this field, but it may choose a node that violates
                              one or more of the expressions. The node that is most
                              preferred is the one with the greatest sum of weights,
                              i.e. for each node that meets all of the scheduling
                              requirements (resource request, requiredDuringScheduling
                              affinity expressions, etc.), compute a sum by iterating
                              through the elements of this field and adding "weight"
                              to the sum if the node has pods which matches the corresponding
                              podAffinityTerm; the node(s) with the highest sum are
                              the most preferred.
                            items:
                              description: The weights of all of the matched WeightedPodAffinityTerm
                                fields are added per-node to find the most preferred
                                node(s)
                              properties:
                                podAffinityTerm:
                                  description: Required. A pod affinity term, associated
                                    with the corresponding weight.
                                  properties:
                                    labelSelector:
                                      description: A label query over a set of resources,
                                        in this case pods.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaceSelector:
                                      description: A label query over the set of namespaces
                                        that the term applies to. The term is applied
                                        to the union of the namespaces selected by
                                        this field and the ones listed in the namespaces
                                        field. null selector and null or empty namespaces
                                        list means "this pod's namespace". An empty
                                        selector ({}) matches all namespaces. This
                                        field is beta-level and is only honored when
                                        PodAffinityNamespaceSelector feature is enabled.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaces:
                                      description: namespaces specifies a static list
                                        of namespace names that the term applies to.
                                        The term is applied to the union of the namespaces
                                        listed in this field and the ones selected
                                        by namespaceSelector. null or empty namespaces
                                        list and null namespaceSelector means "this
                                        pod's namespace"
                                      items:
                                        type: string
                                      type: array
                                    topologyKey:
                                      description: This pod should be co-located (affinity)
                                        or not co-located (anti-affinity) with the
                                        pods matching the labelSelector in the specified
                                        namespaces, where co-located is defined as
                                        running on a node whose value of the label
                                        with key topologyKey matches that of any node
                                        on which any of the selected pods is running.
                                        Empty topologyKey is not allowed.
                                      type: string
                                  required:
                                  - topologyKey
                                  type: object
                                weight:
                                  description: weight associated with matching the
                                    corresponding podAffinityTerm, in the range 1-100.
                                  format: int32
                                  type: integer
                              required:
                              - podAffinityTerm
                              - weight
                              type: object
                            type: array
                          requiredDuringSchedulingIgnoredDuringExecution:
                            description: If the affinity requirements specified by
                              this field are not met at scheduling time, the pod will
                              not be scheduled onto the node. If the affinity requirements
                              specified by this field cease to be met at some point
                              during pod execution (e.g. due to a pod label update),
                              the system may or may not try to eventually evict the
                              pod from its node. When there are multiple elements,
                              the lists of nodes corresponding to each podAffinityTerm
                              are intersected, i.e. all terms must be satisfied.
                            items:
                              description: Defines a set of pods (namely those matching
                                the labelSelector relative to the given namespace(s))
                                that this pod should be co-located (affinity) or not
                                co-located (anti-affinity) with, where co-located
                                is defined as running on a node whose value of the
                                label with key <topologyKey> matches that of any node
                                on which a pod of the set of pods is running
                              properties:
                                labelSelector:
                                  description: A label query over a set of resources,
                                    in this case pods.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaceSelector:
                                  description: A label query over the set of namespaces
                                    that the term applies to. The term is applied
                                    to the union of the namespaces selected by this
                                    field and the ones listed in the namespaces field.
                                    null selector and null or empty namespaces list
                                    means "this pod's namespace". An empty selector
                                    ({}) matches all namespaces. This field is beta-level
                                    and is only honored when PodAffinityNamespaceSelector
                                    feature is enabled.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaces:
                                  description: namespaces specifies a static list
                                    of namespace names that the term applies to. The
                                    term is applied to the union of the namespaces
                                    listed in this field and the ones selected by
                                    namespaceSelector. null or empty namespaces list
                                    and null namespaceSelector means "this pod's namespace"
                                  items:
                                    type: string
                                  type: array
                                topologyKey:
                                  description: This pod should be co-located (affinity)
                                    or not co-located (anti-affinity) with the pods
                                    matching the labelSelector in the specified namespaces,
                                    where co-located is defined as running on a node
                                    whose value of the label with key topologyKey
                                    matches that of any node on which any of the selected
                                    pods is running. Empty topologyKey is not allowed.
                                  type: string
                              required:
                              - topologyKey
                              type: object
                            type: array
                        type: object
                      podAntiAffinity:
                        description: Describes pod anti-affinity scheduling rules
                          (e.g. avoid putting this pod in the same node, zone, etc.
                          as some other pod(s)).
                        properties:
                          preferredDuringSchedulingIgnoredDuringExecution:
                            description: The scheduler will prefer to schedule pods
                              to nodes that satisfy the anti-affinity expressions
                              specified by this field, but it may choose a node that
                              violates one or more of the expressions. The node that
                              is most preferred is the one with the greatest sum of
                              weights, i.e. for each node that meets all of the scheduling
                              requirements (resource request, requiredDuringScheduling
                              anti-affinity expressions, etc.), compute a sum by iterating
                              through the elements of this field and adding "weight"
                              to the sum if the node has pods which matches the corresponding
                              podAffinityTerm; the node(s) with the highest sum are
                              the most preferred.
                            items:
                              description: The weights of all of the matched WeightedPodAffinityTerm
                                fields are added per-node to find the most preferred
                                node(s)
                              properties:
                                podAffinityTerm:
                                  description: Required. A pod affinity term, associated
                                    with the corresponding weight.
                                  properties:
                                    labelSelector:
                                      description: A label query over a set of resources,
                                        in this case pods.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaceSelector:
                                      description: A label query over the set of namespaces
                                        that the term applies to. The term is applied
                                        to the union of the namespaces selected by
                                        this field and the ones listed in the namespaces
                                        field. null selector and null or empty namespaces
                                        list means "this pod's namespace". An empty
                                        selector ({}) matches all namespaces. This
                                        field is beta-level and is only honored when
                                        PodAffinityNamespaceSelector feature is enabled.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaces:
                                      description: namespaces specifies a static list
                                        of namespace names that the term applies to.
                                        The term is applied to the union of the namespaces
                                        listed in this field and the ones selected
                                        by namespaceSelector. null or empty namespaces
                                        list and null namespaceSelector means "this
                                        pod's namespace"
                                      items:
                                        type: string
                                      type: array
                                    topologyKey:
                                      description: This pod should be co-located (affinity)
                                        or not co-located (anti-affinity) with the
                                        pods matching the labelSelector in the specified
                                        namespaces, where co-located is defined as
                                        running on a node whose value of the label
                                        with key topologyKey matches that of any node
                                        on which any of the selected pods is running.
                                        Empty topologyKey is not allowed.
                                      type: string
                                  required:
                                  - topologyKey
                                  type: object
                                weight:
                                  description: weight associated with matching the
                                    corresponding podAffinityTerm, in the range 1-100.
                                  format: int32
                                  type: integer
                              required:
                              - podAffinityTerm
                              - weight
                              type: object
                            type: array
                          requiredDuringSchedulingIgnoredDuringExecution:
                            description: If the anti-affinity requirements specified
                              by this field are not met at scheduling time, the pod
                              will not be scheduled onto the node. If the anti-affinity
                              requirements specified by this field cease to be met
                              at some point during pod execution (e.g. due to a pod
                              label update), the system may or may not try to eventually
                              evict the pod from its node. When there are multiple
                              elements, the lists of nodes corresponding to each podAffinityTerm
                              are intersected, i.e. all terms must be satisfied.
                            items:
                              description: Defines a set of pods (namely those matching
                                the labelSelector relative to the given namespace(s))
                                that this pod should be co-located (affinity) or not
                                co-located (anti-affinity) with, where co-located
                                is defined as running on a node whose value of the
                                label with key <topologyKey> matches that of any node
                                on which a pod of the set of pods is running
                              properties:
                                labelSelector:
                                  description: A label query over a set of resources,
                                    in this case pods.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaceSelector:
                                  description: A label query over the set of namespaces
                                    that the term applies to. The term is applied
                                    to the union of the namespaces selected by this
                                    field and the ones listed in the namespaces field.
                                    null selector and null or empty namespaces list
                                    means "this pod's namespace". An empty selector
                                    ({}) matches all namespaces. This field is beta-level
                                    and is only honored when PodAffinityNamespaceSelector
                                    feature is enabled.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaces:
                                  description: namespaces specifies a static list
                                    of namespace names that the term applies to. The
                                    term is applied to the union of the namespaces
                                    listed in this field and the ones selected by
                                    namespaceSelector. null or empty namespaces list
                                    and null namespaceSelector means "this pod's namespace"
                                  items:
                                    type: string
                                  type: array
                                topologyKey:
                                  description: This pod should be co-located (affinity)
                                    or not co-located (anti-affinity) with the pods
                                    matching the labelSelector in the specified namespaces,
                                    where co-located is defined as running on a node
                                    whose value of the label with key topologyKey
                                    matches that of any node on which any of the selected
                                    pods is running. Empty topologyKey is not allowed.
                                  type: string
                              required:
                              - topologyKey
                              type: object
                            type: array
                        type: object
                    type: object
                  command:
                    items:
                      type: string
                    type: array
                  customCommandRenames:
                    items:
                      description: RedisCommandRename defines the specification of
                        a "rename-command" configuration option
                      properties:
                        from:
                          type: string
                        to:
                          type: string
                      type: object
                    type: array
                  customConfig:
                    items:
                      type: string
                    type: array
                  dnsPolicy:
                    description: DNSPolicy defines how a pod's DNS will be configured.
                    type: string
                  exporter:
                    description: RedisExporter defines the specification for the redis
                      exporter
                    properties:
                      args:
                        items:
                          type: string
                        type: array
                      enabled:
                        type: boolean
                      env:
                        items:
                          description: EnvVar represents an environment variable present
                            in a Container.
                          properties:
                            name:
                              description: Name of the environment variable. Must
                                be a C_IDENTIFIER.
                              type: string
                            value:
                              description: 'Variable references $(VAR_NAME) are expanded
                                using the previously defined environment variables
                                in the container and any service environment variables.
                                If a variable cannot be resolved, the reference in
                                the input string will be unchanged. Double $$ are
                                reduced to a single $, which allows for escaping the
                                $(VAR_NAME) syntax: i.e. "$$(VAR_NAME)" will produce
                                the string literal "$(VAR_NAME)". Escaped references
                                will never be expanded, regardless of whether the
                                variable exists or not. Defaults to "".'
                              type: string
                            valueFrom:
                              description: Source for the environment variable's value.
                                Cannot be used if value is not empty.
                              properties:
                                configMapKeyRef:
                                  description: Selects a key of a ConfigMap.
                                  properties:
                                    key:
                                      description: The key to select.
                                      type: string
                                    name:
                                      description: 'Name of the referent. More info:
                                        https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
                                        TODO: Add other useful fields. apiVersion,
                                        kind, uid?'
                                      type: string
                                    optional:
                                      description: Specify whether the ConfigMap or
                                        its key must be defined
                                      type: boolean
                                  required:
                                  - key
                                  type: object
                                fieldRef:
                                  description: 'Selects a field of the pod: supports
                                    metadata.name, metadata.namespace, `metadata.labels[''<KEY>'']`,
                                    `metadata.annotations[''<KEY>'']`, spec.nodeName,
                                    spec.serviceAccountName, status.hostIP, status.podIP,
                                    status.podIPs.'
                                  properties:
                                    apiVersion:
                                      description: Version of the schema the FieldPath
                                        is written in terms of, defaults to "v1".
                                      type: string
                                    fieldPath:
                                      description: Path of the field to select in
                                        the specified API version.
                                      type: string
                                  required:
                                  - fieldPath
                                  type: object
                                resourceFieldRef:
                                  description: 'Selects a resource of the container:
                                    only resources limits and requests (limits.cpu,
                                    limits.memory, limits.ephemeral-storage, requests.cpu,
                                    requests.memory and requests.ephemeral-storage)
                                    are currently supported.'
                                  properties:
                                    containerName:
                                      description: 'Container name: required for volumes,
                                        optional for env vars'
                                      type: string
                                    divisor:
                                      anyOf:
                                      - type: integer
                                      - type: string
                                      description: Specifies the output format of
                                        the exposed resources, defaults to "1"
                                      pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                                      x-kubernetes-int-or-string: true
                                    resource:
                                      description: 'Required: resource to select'
                                      type: string
                                  required:
                                  - resource
                                  type: object
                                secretKeyRef:
                                  description: Selects a key of a secret in the pod's
                                    namespace
                                  properties:
                                    key:
                                      description: The key of the secret to select
                                        from.  Must be a valid secret key.
                                      type: string
                                    name:
                                      description: 'Name of the referent. More info:
                                        https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
                                        TODO: Add other useful fields. apiVersion,
                                        kind, uid?'
                                      type: string
                                    optional:
                                      description: Specify whether the Secret or its
                                        key must be defined
                                      type: boolean
                                  required:
                                  - key
                                  type: object
                              type: object
                          required:
                          - name
                          type: object
                        type: array
                      image:
                        type: string
                      imagePullPolicy:
                        description: PullPolicy describes a policy for if/when to
                          pull a container image
                        type: string
                      resources:
                        description: ResourceRequirements describes the compute resource
                          requirements.
                        properties:
                          limits:
                            additionalProperties:
                              anyOf:
                              - type: integer
                              - type: string
                              pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                              x-kubernetes-int-or-string: true
                            description: 'Limits describes the maximum amount of compute
                              resources allowed. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                            type: object
                          requests:
                            additionalProperties:
                              anyOf:
                              - type: integer
                              - type: string
                              pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                              x-kubernetes-int-or-string: true
                            description: 'Requests describes the minimum amount of
                              compute resources required. If Requests is omitted for
                              a container, it defaults to Limits if that is explicitly
                              specified, otherwise to an implementation-defined value.
                              More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                            type: object
                        type: object
                    type: object
                  hostNetwork:
                    type: boolean
                  image:
                    type: string
                  imagePullPolicy:
                    description: PullPolicy describes a policy for if/when to pull
                      a container image
                    type: string
                  imagePullSecrets:
                    items:
                      description: LocalObjectReference contains enough information
                        to let you locate the referenced object inside the same namespace.
                      properties:
                        name:
                          description: 'Name of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
                            TODO: Add other useful fields. apiVersion, kind, uid?'
                          type: string
                      type: object
                    type: array
                  nodeSelector:
                    additionalProperties:
                      type: string
                    type: object
                  podAnnotations:
                    additionalProperties:
                      type: string
                    type: object
                  priorityClassName:
                    type: string
                  replicas:
                    format: int32
                    type: integer
                  resources:
                    description: ResourceRequirements describes the compute resource
                      requirements.
                    properties:
                      limits:
                        additionalProperties:
                          anyOf:
                          - type: integer
                          - type: string
                          pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                          x-kubernetes-int-or-string: true
                        description: 'Limits describes the maximum amount of compute
                          resources allowed. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                        type: object
                      requests:
                        additionalProperties:
                          anyOf:
                          - type: integer
                          - type: string
                          pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                          x-kubernetes-int-or-string: true
                        description: 'Requests describes the minimum amount of compute
                          resources required. If Requests is omitted for a container,
                          it defaults to Limits if that is explicitly specified, otherwise
                          to an implementation-defined value. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                        type: object
                    type: object
                  securityContext:
                    description: PodSecurityContext holds pod-level security attributes
                      and common container settings. Some fields are also present
                      in container.securityContext.  Field values of container.securityContext
                      take precedence over field values of PodSecurityContext.
                    properties:
                      fsGroup:
                        description: "A special supplemental group that applies to
                          all containers in a pod. Some volume types allow the Kubelet
                          to change the ownership of that volume to be owned by the
                          pod: \n 1. The owning GID will be the FSGroup 2. The setgid
                          bit is set (new files created in the volume will be owned
                          by FSGroup) 3. The permission bits are OR'd with rw-rw----
                          \n If unset, the Kubelet will not modify the ownership and
                          permissions of any volume."
                        format: int64
                        type: integer
                      fsGroupChangePolicy:
                        description: 'fsGroupChangePolicy defines behavior of changing
                          ownership and permission of the volume before being exposed
                          inside Pod. This field will only apply to volume types which
                          support fsGroup based ownership(and permissions). It will
                          have no effect on ephemeral volume types such as: secret,
                          configmaps and emptydir. Valid values are "OnRootMismatch"
                          and "Always". If not specified, "Always" is used.'
                        type: string
                      runAsGroup:
                        description: The GID to run the entrypoint of the container
                          process. Uses runtime default if unset. May also be set
                          in SecurityContext.  If set in both SecurityContext and
                          PodSecurityContext, the value specified in SecurityContext
                          takes precedence for that container.
                        format: int64
                        type: integer
                      runAsNonRoot:
                        description: Indicates that the container must run as a non-root
                          user. If true, the Kubelet will validate the image at runtime
                          to ensure that it does not run as UID 0 (root) and fail
                          to start the container if it does. If unset or false, no
                          such validation will be performed. May also be set in SecurityContext.  If
                          set in both SecurityContext and PodSecurityContext, the
                          value specified in SecurityContext takes precedence.
                        type: boolean
                      runAsUser:
                        description: The UID to run the entrypoint of the container
                          process. Defaults to user specified in image metadata if
                          unspecified. May also be set in SecurityContext.  If set
                          in both SecurityContext and PodSecurityContext, the value
                          specified in SecurityContext takes precedence for that container.
                        format: int64
                        type: integer
                      seLinuxOptions:
                        description: The SELinux context to be applied to all containers.
                          If unspecified, the container runtime will allocate a random
                          SELinux context for each container.  May also be set in
                          SecurityContext.  If set in both SecurityContext and PodSecurityContext,
                          the value specified in SecurityContext takes precedence
                          for that container.
                        properties:
                          level:
                            description: Level is SELinux level label that applies
                              to the container.
                            type: string
                          role:
                            description: Role is a SELinux role label that applies
                              to the container.
                            type: string
                          type:
                            description: Type is a SELinux type label that applies
                              to the container.
                            type: string
                          user:
                            description: User is a SELinux user label that applies
                              to the container.
                            type: string
                        type: object
                      seccompProfile:
                        description: The seccomp options to use by the containers
                          in this pod.
                        properties:
                          localhostProfile:
                            description: localhostProfile indicates a profile defined
                              in a file on the node should be used. The profile must
                              be preconfigured on the node to work. Must be a descending
                              path, relative to the kubelet's configured seccomp profile
                              location. Must only be set if type is "Localhost".
                            type: string
                          type:
                            description: "type indicates which kind of seccomp profile
                              will be applied. Valid options are: \n Localhost - a
                              profile defined in a file on the node should be used.
                              RuntimeDefault - the container runtime default profile
                              should be used. Unconfined - no profile should be applied."
                            type: string
                        required:
                        - type
                        type: object
                      supplementalGroups:
                        description: A list of groups applied to the first process
                          run in each container, in addition to the container's primary
                          GID.  If unspecified, no groups will be added to any container.
                        items:
                          format: int64
                          type: integer
                        type: array
                      sysctls:
                        description: Sysctls hold a list of namespaced sysctls used
                          for the pod. Pods with unsupported sysctls (by the container
                          runtime) might fail to launch.
                        items:
                          description: Sysctl defines a kernel parameter to be set
                          properties:
                            name:
                              description: Name of a property to set
                              type: string
                            value:
                              description: Value of a property to set
                              type: string
                          required:
                          - name
                          - value
                          type: object
                        type: array
                      windowsOptions:
                        description: The Windows specific settings applied to all
                          containers. If unspecified, the options within a container's
                          SecurityContext will be used. If set in both SecurityContext
                          and PodSecurityContext, the value specified in SecurityContext
                          takes precedence.
                        properties:
                          gmsaCredentialSpec:
                            description: GMSACredentialSpec is where the GMSA admission
                              webhook (https://github.com/kubernetes-sigs/windows-gmsa)
                              inlines the contents of the GMSA credential spec named
                              by the GMSACredentialSpecName field.
                            type: string
                          gmsaCredentialSpecName:
                            description: GMSACredentialSpecName is the name of the
                              GMSA credential spec to use.
                            type: string
                          hostProcess:
                            description: HostProcess determines if a container should
                              be run as a 'Host Process' container. This field is
                              alpha-level and will only be honored by components that
                              enable the WindowsHostProcessContainers feature flag.
                              Setting this field without the feature flag will result
                              in errors when validating the Pod. All of a Pod's containers
                              must have the same effective HostProcess value (it is
                              not allowed to have a mix of HostProcess containers
                              and non-HostProcess containers).  In addition, if HostProcess
                              is true then HostNetwork must also be set to true.
                            type: boolean
                          runAsUserName:
                            description: The UserName in Windows to run the entrypoint
                              of the container process. Defaults to the user specified
                              in image metadata if unspecified. May also be set in
                              PodSecurityContext. If set in both SecurityContext and
                              PodSecurityContext, the value specified in SecurityContext
                              takes precedence.
                            type: string
                        type: object
                    type: object
                  serviceAccountName:
                    type: string
                  serviceAnnotations:
                    additionalProperties:
                      type: string
                    type: object
                  shutdownConfigMap:
                    type: string
                  storage:
                    description: RedisStorage defines the structure used to store
                      the Redis Data
                    properties:
                      emptyDir:
                        description: Represents an empty directory for a pod. Empty
                          directory volumes support ownership management and SELinux
                          relabeling.
                        properties:
                          medium:
                            description: 'What type of storage medium should back
                              this directory. The default is "" which means to use
                              the node''s default medium. Must be an empty string
                              (default) or Memory. More info: https://kubernetes.io/docs/concepts/storage/volumes#emptydir'
                            type: string
                          sizeLimit:
                            anyOf:
                            - type: integer
                            - type: string
                            description: 'Total amount of local storage required for
                              this EmptyDir volume. The size limit is also applicable
                              for memory medium. The maximum usage on memory medium
                              EmptyDir would be the minimum value between the SizeLimit
                              specified here and the sum of memory limits of all containers
                              in a pod. The default is nil which means that the limit
                              is undefined. More info: http://kubernetes.io/docs/user-guide/volumes#emptydir'
                            pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                            x-kubernetes-int-or-string: true
                        type: object
                      keepAfterDeletion:
                        type: boolean
                      persistentVolumeClaim:
                        description: EmbeddedPersistentVolumeClaim is an embedded
                          version of k8s.io/api/core/v1.PersistentVolumeClaim. It
                          contains TypeMeta and a reduced ObjectMeta.
                        properties:
                          apiVersion:
                            description: 'APIVersion defines the versioned schema
                              of this representation of an object. Servers should
                              convert recognized schemas to the latest internal value,
                              and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources'
                            type: string
                          kind:
                            description: 'Kind is a string value representing the
                              REST resource this object represents. Servers may infer
                              this from the endpoint the client submits requests to.
                              Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds'
                            type: string
                          metadata:
                            description: EmbeddedMetadata contains metadata relevant
                              to an EmbeddedResource.
                            properties:
                              annotations:
                                additionalProperties:
                                  type: string
                                description: 'Annotations is an unstructured key value
                                  map stored with a resource that may be set by external
                                  tools to store and retrieve arbitrary metadata.
                                  They are not queryable and should be preserved when
                                  modifying objects. More info: http://kubernetes.io/docs/user-guide/annotations'
                                type: object
                              labels:
                                additionalProperties:
                                  type: string
                                description: 'Map of string keys and values that can
                                  be used to organize and categorize (scope and select)
                                  objects. May match selectors of replication controllers
                                  and services. More info: http://kubernetes.io/docs/user-guide/labels'
                                type: object
                              name:
                                description: 'Name must be unique within a namespace.
                                  Is required when creating resources, although some
                                  resources may allow a client to request the generation
                                  of an appropriate name automatically. Name is primarily
                                  intended for creation idempotence and configuration
                                  definition. Cannot be updated. More info: http://kubernetes.io/docs/user-guide/identifiers#names'
                                type: string
                            type: object
                          spec:
                            description: 'Spec defines the desired characteristics
                              of a volume requested by a pod author. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistentvolumeclaims'
                            properties:
                              accessModes:
                                description: 'AccessModes contains the desired access
                                  modes the volume should have. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes-1'
                                items:
                                  type: string
                                type: array
                              dataSource:
                                description: 'This field can be used to specify either:
                                  * An existing VolumeSnapshot object (snapshot.storage.k8s.io/VolumeSnapshot)
                                  * An existing PVC (PersistentVolumeClaim) If the
                                  provisioner or an external controller can support
                                  the specified data source, it will create a new
                                  volume based on the contents of the specified data
                                  source. If the AnyVolumeDataSource feature gate
                                  is enabled, this field will always have the same
                                  contents as the DataSourceRef field.'
                                properties:
                                  apiGroup:
                                    description: APIGroup is the group for the resource
                                      being referenced. If APIGroup is not specified,
                                      the specified Kind must be in the core API group.
                                      For any other third-party types, APIGroup is
                                      required.
                                    type: string
                                  kind:
                                    description: Kind is the type of resource being
                                      referenced
                                    type: string
                                  name:
                                    description: Name is the name of resource being
                                      referenced
                                    type: string
                                required:
                                - kind
                                - name
                                type: object
                              dataSourceRef:
                                description: 'Specifies the object from which to populate
                                  the volume with data, if a non-empty volume is desired.
                                  This may be any local object from a non-empty API
                                  group (non core object) or a PersistentVolumeClaim
                                  object. When this field is specified, volume binding
                                  will only succeed if the type of the specified object
                                  matches some installed volume populator or dynamic
                                  provisioner. This field will replace the functionality
                                  of the DataSource field and as such if both fields
                                  are non-empty, they must have the same value. For
                                  backwards compatibility, both fields (DataSource
                                  and DataSourceRef) will be set to the same value
                                  automatically if one of them is empty and the other
                                  is non-empty. There are two important differences
                                  between DataSource and DataSourceRef: * While DataSource
                                  only allows two specific types of objects, DataSourceRef   allows
                                  any non-core object, as well as PersistentVolumeClaim
                                  objects. * While DataSource ignores disallowed values
                                  (dropping them), DataSourceRef   preserves all values,
                                  and generates an error if a disallowed value is   specified.
                                  (Alpha) Using this field requires the AnyVolumeDataSource
                                  feature gate to be enabled.'
                                properties:
                                  apiGroup:
                                    description: APIGroup is the group for the resource
                                      being referenced. If APIGroup is not specified,
                                      the specified Kind must be in the core API group.
                                      For any other third-party types, APIGroup is
                                      required.
                                    type: string
                                  kind:
                                    description: Kind is the type of resource being
                                      referenced
                                    type: string
                                  name:
                                    description: Name is the name of resource being
                                      referenced
                                    type: string
                                required:
                                - kind
                                - name
                                type: object
                              resources:
                                description: 'Resources represents the minimum resources
                                  the volume should have. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#resources'
                                properties:
                                  limits:
                                    additionalProperties:
                                      anyOf:
                                      - type: integer
                                      - type: string
                                      pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                                      x-kubernetes-int-or-string: true
                                    description: 'Limits describes the maximum amount
                                      of compute resources allowed. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                                    type: object
                                  requests:
                                    additionalProperties:
                                      anyOf:
                                      - type: integer
                                      - type: string
                                      pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                                      x-kubernetes-int-or-string: true
                                    description: 'Requests describes the minimum amount
                                      of compute resources required. If Requests is
                                      omitted for a container, it defaults to Limits
                                      if that is explicitly specified, otherwise to
                                      an implementation-defined value. More info:
                                      https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                                    type: object
                                type: object
                              selector:
                                description: A label query over volumes to consider
                                  for binding.
                                properties:
                                  matchExpressions:
                                    description: matchExpressions is a list of label
                                      selector requirements. The requirements are
                                      ANDed.
                                    items:
                                      description: A label selector requirement is
                                        a selector that contains values, a key, and
                                        an operator that relates the key and values.
                                      properties:
                                        key:
                                          description: key is the label key that the
                                            selector applies to.
                                          type: string
                                        operator:
                                          description: operator represents a key's
                                            relationship to a set of values. Valid
                                            operators are In, NotIn, Exists and DoesNotExist.
                                          type: string
                                        values:
                                          description: values is an array of string
                                            values. If the operator is In or NotIn,
                                            the values array must be non-empty. If
                                            the operator is Exists or DoesNotExist,
                                            the values array must be empty. This array
                                            is replaced during a strategic merge patch.
                                          items:
                                            type: string
                                          type: array
                                      required:
                                      - key
                                      - operator
                                      type: object
                                    type: array
                                  matchLabels:
                                    additionalProperties:
                                      type: string
                                    description: matchLabels is a map of {key,value}
                                      pairs. A single {key,value} in the matchLabels
                                      map is equivalent to an element of matchExpressions,
                                      whose key field is "key", the operator is "In",
                                      and the values array contains only "value".
                                      The requirements are ANDed.
                                    type: object
                                type: object
                              storageClassName:
                                description: 'Name of the StorageClass required by
                                  the claim. More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#class-1'
                                type: string
                              volumeMode:
                                description: volumeMode defines what type of volume
                                  is required by the claim. Value of Filesystem is
                                  implied when not included in claim spec.
                                type: string
                              volumeName:
                                description: VolumeName is the binding reference to
                                  the PersistentVolume backing this claim.
                                type: string
                            type: object
                          status:
                            description: 'Status represents the current information/status
                              of a persistent volume claim. Read-only. More info:
                              https://kubernetes.io/docs/concepts/storage/persistent-volumes#persistentvolumeclaims'
                            properties:
                              accessModes:
                                description: 'AccessModes contains the actual access
                                  modes the volume backing the PVC has. More info:
                                  https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes-1'
                                items:
                                  type: string
                                type: array
                              capacity:
                                additionalProperties:
                                  anyOf:
                                  - type: integer
                                  - type: string
                                  pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                                  x-kubernetes-int-or-string: true
                                description: Represents the actual resources of the
                                  underlying volume.
                                type: object
                              conditions:
                                description: Current Condition of persistent volume
                                  claim. If underlying persistent volume is being
                                  resized then the Condition will be set to 'ResizeStarted'.
                                items:
                                  description: PersistentVolumeClaimCondition contails
                                    details about state of pvc
                                  properties:
                                    lastProbeTime:
                                      description: Last time we probed the condition.
                                      format: date-time
                                      type: string
                                    lastTransitionTime:
                                      description: Last time the condition transitioned
                                        from one status to another.
                                      format: date-time
                                      type: string
                                    message:
                                      description: Human-readable message indicating
                                        details about last transition.
                                      type: string
                                    reason:
                                      description: Unique, this should be a short,
                                        machine understandable string that gives the
                                        reason for condition's last transition. If
                                        it reports "ResizeStarted" that means the
                                        underlying persistent volume is being resized.
                                      type: string
                                    status:
                                      type: string
                                    type:
                                      description: PersistentVolumeClaimConditionType
                                        is a valid value of PersistentVolumeClaimCondition.Type
                                      type: string
                                  required:
                                  - status
                                  - type
                                  type: object
                                type: array
                              phase:
                                description: Phase represents the current phase of
                                  PersistentVolumeClaim.
                                type: string
                            type: object
                        type: object
                    type: object
                  terminationGracePeriod:
                    format: int64
                    type: integer
                  tolerations:
                    items:
                      description: The pod this Toleration is attached to tolerates
                        any taint that matches the triple <key,value,effect> using
                        the matching operator <operator>.
                      properties:
                        effect:
                          description: Effect indicates the taint effect to match.
                            Empty means match all taint effects. When specified, allowed
                            values are NoSchedule, PreferNoSchedule and NoExecute.
                          type: string
                        key:
                          description: Key is the taint key that the toleration applies
                            to. Empty means match all taint keys. If the key is empty,
                            operator must be Exists; this combination means to match
                            all values and all keys.
                          type: string
                        operator:
                          description: Operator represents a key's relationship to
                            the value. Valid operators are Exists and Equal. Defaults
                            to Equal. Exists is equivalent to wildcard for value,
                            so that a pod can tolerate all taints of a particular
                            category.
                          type: string
                        tolerationSeconds:
                          description: TolerationSeconds represents the period of
                            time the toleration (which must be of effect NoExecute,
                            otherwise this field is ignored) tolerates the taint.
                            By default, it is not set, which means tolerate the taint
                            forever (do not evict). Zero and negative values will
                            be treated as 0 (evict immediately) by the system.
                          format: int64
                          type: integer
                        value:
                          description: Value is the taint value the toleration matches
                            to. If the operator is Exists, the value should be empty,
                            otherwise just a regular string.
                          type: string
                      type: object
                    type: array
                type: object
              sentinel:
                description: SentinelSettings defines the specification of the sentinel
                  cluster
                properties:
                  affinity:
                    description: Affinity is a group of affinity scheduling rules.
                    properties:
                      nodeAffinity:
                        description: Describes node affinity scheduling rules for
                          the pod.
                        properties:
                          preferredDuringSchedulingIgnoredDuringExecution:
                            description: The scheduler will prefer to schedule pods
                              to nodes that satisfy the affinity expressions specified
                              by this field, but it may choose a node that violates
                              one or more of the expressions. The node that is most
                              preferred is the one with the greatest sum of weights,
                              i.e. for each node that meets all of the scheduling
                              requirements (resource request, requiredDuringScheduling
                              affinity expressions, etc.), compute a sum by iterating
                              through the elements of this field and adding "weight"
                              to the sum if the node matches the corresponding matchExpressions;
                              the node(s) with the highest sum are the most preferred.
                            items:
                              description: An empty preferred scheduling term matches
                                all objects with implicit weight 0 (i.e. it's a no-op).
                                A null preferred scheduling term matches no objects
                                (i.e. is also a no-op).
                              properties:
                                preference:
                                  description: A node selector term, associated with
                                    the corresponding weight.
                                  properties:
                                    matchExpressions:
                                      description: A list of node selector requirements
                                        by node's labels.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchFields:
                                      description: A list of node selector requirements
                                        by node's fields.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                  type: object
                                weight:
                                  description: Weight associated with matching the
                                    corresponding nodeSelectorTerm, in the range 1-100.
                                  format: int32
                                  type: integer
                              required:
                              - preference
                              - weight
                              type: object
                            type: array
                          requiredDuringSchedulingIgnoredDuringExecution:
                            description: If the affinity requirements specified by
                              this field are not met at scheduling time, the pod will
                              not be scheduled onto the node. If the affinity requirements
                              specified by this field cease to be met at some point
                              during pod execution (e.g. due to an update), the system
                              may or may not try to eventually evict the pod from
                              its node.
                            properties:
                              nodeSelectorTerms:
                                description: Required. A list of node selector terms.
                                  The terms are ORed.
                                items:
                                  description: A null or empty node selector term
                                    matches no objects. The requirements of them are
                                    ANDed. The TopologySelectorTerm type implements
                                    a subset of the NodeSelectorTerm.
                                  properties:
                                    matchExpressions:
                                      description: A list of node selector requirements
                                        by node's labels.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchFields:
                                      description: A list of node selector requirements
                                        by node's fields.
                                      items:
                                        description: A node selector requirement is
                                          a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: The label key that the selector
                                              applies to.
                                            type: string
                                          operator:
                                            description: Represents a key's relationship
                                              to a set of values. Valid operators
                                              are In, NotIn, Exists, DoesNotExist.
                                              Gt, and Lt.
                                            type: string
                                          values:
                                            description: An array of string values.
                                              If the operator is In or NotIn, the
                                              values array must be non-empty. If the
                                              operator is Exists or DoesNotExist,
                                              the values array must be empty. If the
                                              operator is Gt or Lt, the values array
                                              must have a single element, which will
                                              be interpreted as an integer. This array
                                              is replaced during a strategic merge
                                              patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                  type: object
                                type: array
                            required:
                            - nodeSelectorTerms
                            type: object
                        type: object
                      podAffinity:
                        description: Describes pod affinity scheduling rules (e.g.
                          co-locate this pod in the same node, zone, etc. as some
                          other pod(s)).
                        properties:
                          preferredDuringSchedulingIgnoredDuringExecution:
                            description: The scheduler will prefer to schedule pods
                              to nodes that satisfy the affinity expressions specified
                              by this field, but it may choose a node that violates
                              one or more of the expressions. The node that is most
                              preferred is the one with the greatest sum of weights,
                              i.e. for each node that meets all of the scheduling
                              requirements (resource request, requiredDuringScheduling
                              affinity expressions, etc.), compute a sum by iterating
                              through the elements of this field and adding "weight"
                              to the sum if the node has pods which matches the corresponding
                              podAffinityTerm; the node(s) with the highest sum are
                              the most preferred.
                            items:
                              description: The weights of all of the matched WeightedPodAffinityTerm
                                fields are added per-node to find the most preferred
                                node(s)
                              properties:
                                podAffinityTerm:
                                  description: Required. A pod affinity term, associated
                                    with the corresponding weight.
                                  properties:
                                    labelSelector:
                                      description: A label query over a set of resources,
                                        in this case pods.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaceSelector:
                                      description: A label query over the set of namespaces
                                        that the term applies to. The term is applied
                                        to the union of the namespaces selected by
                                        this field and the ones listed in the namespaces
                                        field. null selector and null or empty namespaces
                                        list means "this pod's namespace". An empty
                                        selector ({}) matches all namespaces. This
                                        field is beta-level and is only honored when
                                        PodAffinityNamespaceSelector feature is enabled.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaces:
                                      description: namespaces specifies a static list
                                        of namespace names that the term applies to.
                                        The term is applied to the union of the namespaces
                                        listed in this field and the ones selected
                                        by namespaceSelector. null or empty namespaces
                                        list and null namespaceSelector means "this
                                        pod's namespace"
                                      items:
                                        type: string
                                      type: array
                                    topologyKey:
                                      description: This pod should be co-located (affinity)
                                        or not co-located (anti-affinity) with the
                                        pods matching the labelSelector in the specified
                                        namespaces, where co-located is defined as
                                        running on a node whose value of the label
                                        with key topologyKey matches that of any node
                                        on which any of the selected pods is running.
                                        Empty topologyKey is not allowed.
                                      type: string
                                  required:
                                  - topologyKey
                                  type: object
                                weight:
                                  description: weight associated with matching the
                                    corresponding podAffinityTerm, in the range 1-100.
                                  format: int32
                                  type: integer
                              required:
                              - podAffinityTerm
                              - weight
                              type: object
                            type: array
                          requiredDuringSchedulingIgnoredDuringExecution:
                            description: If the affinity requirements specified by
                              this field are not met at scheduling time, the pod will
                              not be scheduled onto the node. If the affinity requirements
                              specified by this field cease to be met at some point
                              during pod execution (e.g. due to a pod label update),
                              the system may or may not try to eventually evict the
                              pod from its node. When there are multiple elements,
                              the lists of nodes corresponding to each podAffinityTerm
                              are intersected, i.e. all terms must be satisfied.
                            items:
                              description: Defines a set of pods (namely those matching
                                the labelSelector relative to the given namespace(s))
                                that this pod should be co-located (affinity) or not
                                co-located (anti-affinity) with, where co-located
                                is defined as running on a node whose value of the
                                label with key <topologyKey> matches that of any node
                                on which a pod of the set of pods is running
                              properties:
                                labelSelector:
                                  description: A label query over a set of resources,
                                    in this case pods.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaceSelector:
                                  description: A label query over the set of namespaces
                                    that the term applies to. The term is applied
                                    to the union of the namespaces selected by this
                                    field and the ones listed in the namespaces field.
                                    null selector and null or empty namespaces list
                                    means "this pod's namespace". An empty selector
                                    ({}) matches all namespaces. This field is beta-level
                                    and is only honored when PodAffinityNamespaceSelector
                                    feature is enabled.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaces:
                                  description: namespaces specifies a static list
                                    of namespace names that the term applies to. The
                                    term is applied to the union of the namespaces
                                    listed in this field and the ones selected by
                                    namespaceSelector. null or empty namespaces list
                                    and null namespaceSelector means "this pod's namespace"
                                  items:
                                    type: string
                                  type: array
                                topologyKey:
                                  description: This pod should be co-located (affinity)
                                    or not co-located (anti-affinity) with the pods
                                    matching the labelSelector in the specified namespaces,
                                    where co-located is defined as running on a node
                                    whose value of the label with key topologyKey
                                    matches that of any node on which any of the selected
                                    pods is running. Empty topologyKey is not allowed.
                                  type: string
                              required:
                              - topologyKey
                              type: object
                            type: array
                        type: object
                      podAntiAffinity:
                        description: Describes pod anti-affinity scheduling rules
                          (e.g. avoid putting this pod in the same node, zone, etc.
                          as some other pod(s)).
                        properties:
                          preferredDuringSchedulingIgnoredDuringExecution:
                            description: The scheduler will prefer to schedule pods
                              to nodes that satisfy the anti-affinity expressions
                              specified by this field, but it may choose a node that
                              violates one or more of the expressions. The node that
                              is most preferred is the one with the greatest sum of
                              weights, i.e. for each node that meets all of the scheduling
                              requirements (resource request, requiredDuringScheduling
                              anti-affinity expressions, etc.), compute a sum by iterating
                              through the elements of this field and adding "weight"
                              to the sum if the node has pods which matches the corresponding
                              podAffinityTerm; the node(s) with the highest sum are
                              the most preferred.
                            items:
                              description: The weights of all of the matched WeightedPodAffinityTerm
                                fields are added per-node to find the most preferred
                                node(s)
                              properties:
                                podAffinityTerm:
                                  description: Required. A pod affinity term, associated
                                    with the corresponding weight.
                                  properties:
                                    labelSelector:
                                      description: A label query over a set of resources,
                                        in this case pods.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaceSelector:
                                      description: A label query over the set of namespaces
                                        that the term applies to. The term is applied
                                        to the union of the namespaces selected by
                                        this field and the ones listed in the namespaces
                                        field. null selector and null or empty namespaces
                                        list means "this pod's namespace". An empty
                                        selector ({}) matches all namespaces. This
                                        field is beta-level and is only honored when
                                        PodAffinityNamespaceSelector feature is enabled.
                                      properties:
                                        matchExpressions:
                                          description: matchExpressions is a list
                                            of label selector requirements. The requirements
                                            are ANDed.
                                          items:
                                            description: A label selector requirement
                                              is a selector that contains values,
                                              a key, and an operator that relates
                                              the key and values.
                                            properties:
                                              key:
                                                description: key is the label key
                                                  that the selector applies to.
                                                type: string
                                              operator:
                                                description: operator represents a
                                                  key's relationship to a set of values.
                                                  Valid operators are In, NotIn, Exists
                                                  and DoesNotExist.
                                                type: string
                                              values:
                                                description: values is an array of
                                                  string values. If the operator is
                                                  In or NotIn, the values array must
                                                  be non-empty. If the operator is
                                                  Exists or DoesNotExist, the values
                                                  array must be empty. This array
                                                  is replaced during a strategic merge
                                                  patch.
                                                items:
                                                  type: string
                                                type: array
                                            required:
                                            - key
                                            - operator
                                            type: object
                                          type: array
                                        matchLabels:
                                          additionalProperties:
                                            type: string
                                          description: matchLabels is a map of {key,value}
                                            pairs. A single {key,value} in the matchLabels
                                            map is equivalent to an element of matchExpressions,
                                            whose key field is "key", the operator
                                            is "In", and the values array contains
                                            only "value". The requirements are ANDed.
                                          type: object
                                      type: object
                                    namespaces:
                                      description: namespaces specifies a static list
                                        of namespace names that the term applies to.
                                        The term is applied to the union of the namespaces
                                        listed in this field and the ones selected
                                        by namespaceSelector. null or empty namespaces
                                        list and null namespaceSelector means "this
                                        pod's namespace"
                                      items:
                                        type: string
                                      type: array
                                    topologyKey:
                                      description: This pod should be co-located (affinity)
                                        or not co-located (anti-affinity) with the
                                        pods matching the labelSelector in the specified
                                        namespaces, where co-located is defined as
                                        running on a node whose value of the label
                                        with key topologyKey matches that of any node
                                        on which any of the selected pods is running.
                                        Empty topologyKey is not allowed.
                                      type: string
                                  required:
                                  - topologyKey
                                  type: object
                                weight:
                                  description: weight associated with matching the
                                    corresponding podAffinityTerm, in the range 1-100.
                                  format: int32
                                  type: integer
                              required:
                              - podAffinityTerm
                              - weight
                              type: object
                            type: array
                          requiredDuringSchedulingIgnoredDuringExecution:
                            description: If the anti-affinity requirements specified
                              by this field are not met at scheduling time, the pod
                              will not be scheduled onto the node. If the anti-affinity
                              requirements specified by this field cease to be met
                              at some point during pod execution (e.g. due to a pod
                              label update), the system may or may not try to eventually
                              evict the pod from its node. When there are multiple
                              elements, the lists of nodes corresponding to each podAffinityTerm
                              are intersected, i.e. all terms must be satisfied.
                            items:
                              description: Defines a set of pods (namely those matching
                                the labelSelector relative to the given namespace(s))
                                that this pod should be co-located (affinity) or not
                                co-located (anti-affinity) with, where co-located
                                is defined as running on a node whose value of the
                                label with key <topologyKey> matches that of any node
                                on which a pod of the set of pods is running
                              properties:
                                labelSelector:
                                  description: A label query over a set of resources,
                                    in this case pods.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaceSelector:
                                  description: A label query over the set of namespaces
                                    that the term applies to. The term is applied
                                    to the union of the namespaces selected by this
                                    field and the ones listed in the namespaces field.
                                    null selector and null or empty namespaces list
                                    means "this pod's namespace". An empty selector
                                    ({}) matches all namespaces. This field is beta-level
                                    and is only honored when PodAffinityNamespaceSelector
                                    feature is enabled.
                                  properties:
                                    matchExpressions:
                                      description: matchExpressions is a list of label
                                        selector requirements. The requirements are
                                        ANDed.
                                      items:
                                        description: A label selector requirement
                                          is a selector that contains values, a key,
                                          and an operator that relates the key and
                                          values.
                                        properties:
                                          key:
                                            description: key is the label key that
                                              the selector applies to.
                                            type: string
                                          operator:
                                            description: operator represents a key's
                                              relationship to a set of values. Valid
                                              operators are In, NotIn, Exists and
                                              DoesNotExist.
                                            type: string
                                          values:
                                            description: values is an array of string
                                              values. If the operator is In or NotIn,
                                              the values array must be non-empty.
                                              If the operator is Exists or DoesNotExist,
                                              the values array must be empty. This
                                              array is replaced during a strategic
                                              merge patch.
                                            items:
                                              type: string
                                            type: array
                                        required:
                                        - key
                                        - operator
                                        type: object
                                      type: array
                                    matchLabels:
                                      additionalProperties:
                                        type: string
                                      description: matchLabels is a map of {key,value}
                                        pairs. A single {key,value} in the matchLabels
                                        map is equivalent to an element of matchExpressions,
                                        whose key field is "key", the operator is
                                        "In", and the values array contains only "value".
                                        The requirements are ANDed.
                                      type: object
                                  type: object
                                namespaces:
                                  description: namespaces specifies a static list
                                    of namespace names that the term applies to. The
                                    term is applied to the union of the namespaces
                                    listed in this field and the ones selected by
                                    namespaceSelector. null or empty namespaces list
                                    and null namespaceSelector means "this pod's namespace"
                                  items:
                                    type: string
                                  type: array
                                topologyKey:
                                  description: This pod should be co-located (affinity)
                                    or not co-located (anti-affinity) with the pods
                                    matching the labelSelector in the specified namespaces,
                                    where co-located is defined as running on a node
                                    whose value of the label with key topologyKey
                                    matches that of any node on which any of the selected
                                    pods is running. Empty topologyKey is not allowed.
                                  type: string
                              required:
                              - topologyKey
                              type: object
                            type: array
                        type: object
                    type: object
                  command:
                    items:
                      type: string
                    type: array
                  customConfig:
                    items:
                      type: string
                    type: array
                  dnsPolicy:
                    description: DNSPolicy defines how a pod's DNS will be configured.
                    type: string
                  exporter:
                    description: SentinelExporter defines the specification for the
                      sentinel exporter
                    properties:
                      args:
                        items:
                          type: string
                        type: array
                      enabled:
                        type: boolean
                      env:
                        items:
                          description: EnvVar represents an environment variable present
                            in a Container.
                          properties:
                            name:
                              description: Name of the environment variable. Must
                                be a C_IDENTIFIER.
                              type: string
                            value:
                              description: 'Variable references $(VAR_NAME) are expanded
                                using the previously defined environment variables
                                in the container and any service environment variables.
                                If a variable cannot be resolved, the reference in
                                the input string will be unchanged. Double $$ are
                                reduced to a single $, which allows for escaping the
                                $(VAR_NAME) syntax: i.e. "$$(VAR_NAME)" will produce
                                the string literal "$(VAR_NAME)". Escaped references
                                will never be expanded, regardless of whether the
                                variable exists or not. Defaults to "".'
                              type: string
                            valueFrom:
                              description: Source for the environment variable's value.
                                Cannot be used if value is not empty.
                              properties:
                                configMapKeyRef:
                                  description: Selects a key of a ConfigMap.
                                  properties:
                                    key:
                                      description: The key to select.
                                      type: string
                                    name:
                                      description: 'Name of the referent. More info:
                                        https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
                                        TODO: Add other useful fields. apiVersion,
                                        kind, uid?'
                                      type: string
                                    optional:
                                      description: Specify whether the ConfigMap or
                                        its key must be defined
                                      type: boolean
                                  required:
                                  - key
                                  type: object
                                fieldRef:
                                  description: 'Selects a field of the pod: supports
                                    metadata.name, metadata.namespace, `metadata.labels[''<KEY>'']`,
                                    `metadata.annotations[''<KEY>'']`, spec.nodeName,
                                    spec.serviceAccountName, status.hostIP, status.podIP,
                                    status.podIPs.'
                                  properties:
                                    apiVersion:
                                      description: Version of the schema the FieldPath
                                        is written in terms of, defaults to "v1".
                                      type: string
                                    fieldPath:
                                      description: Path of the field to select in
                                        the specified API version.
                                      type: string
                                  required:
                                  - fieldPath
                                  type: object
                                resourceFieldRef:
                                  description: 'Selects a resource of the container:
                                    only resources limits and requests (limits.cpu,
                                    limits.memory, limits.ephemeral-storage, requests.cpu,
                                    requests.memory and requests.ephemeral-storage)
                                    are currently supported.'
                                  properties:
                                    containerName:
                                      description: 'Container name: required for volumes,
                                        optional for env vars'
                                      type: string
                                    divisor:
                                      anyOf:
                                      - type: integer
                                      - type: string
                                      description: Specifies the output format of
                                        the exposed resources, defaults to "1"
                                      pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                                      x-kubernetes-int-or-string: true
                                    resource:
                                      description: 'Required: resource to select'
                                      type: string
                                  required:
                                  - resource
                                  type: object
                                secretKeyRef:
                                  description: Selects a key of a secret in the pod's
                                    namespace
                                  properties:
                                    key:
                                      description: The key of the secret to select
                                        from.  Must be a valid secret key.
                                      type: string
                                    name:
                                      description: 'Name of the referent. More info:
                                        https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
                                        TODO: Add other useful fields. apiVersion,
                                        kind, uid?'
                                      type: string
                                    optional:
                                      description: Specify whether the Secret or its
                                        key must be defined
                                      type: boolean
                                  required:
                                  - key
                                  type: object
                              type: object
                          required:
                          - name
                          type: object
                        type: array
                      image:
                        type: string
                      imagePullPolicy:
                        description: PullPolicy describes a policy for if/when to
                          pull a container image
                        type: string
                      resources:
                        description: ResourceRequirements describes the compute resource
                          requirements.
                        properties:
                          limits:
                            additionalProperties:
                              anyOf:
                              - type: integer
                              - type: string
                              pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                              x-kubernetes-int-or-string: true
                            description: 'Limits describes the maximum amount of compute
                              resources allowed. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                            type: object
                          requests:
                            additionalProperties:
                              anyOf:
                              - type: integer
                              - type: string
                              pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                              x-kubernetes-int-or-string: true
                            description: 'Requests describes the minimum amount of
                              compute resources required. If Requests is omitted for
                              a container, it defaults to Limits if that is explicitly
                              specified, otherwise to an implementation-defined value.
                              More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                            type: object
                        type: object
                    type: object
                  hostNetwork:
                    type: boolean
                  image:
                    type: string
                  imagePullPolicy:
                    description: PullPolicy describes a policy for if/when to pull
                      a container image
                    type: string
                  imagePullSecrets:
                    items:
                      description: LocalObjectReference contains enough information
                        to let you locate the referenced object inside the same namespace.
                      properties:
                        name:
                          description: 'Name of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
                            TODO: Add other useful fields. apiVersion, kind, uid?'
                          type: string
                      type: object
                    type: array
                  nodeSelector:
                    additionalProperties:
                      type: string
                    type: object
                  podAnnotations:
                    additionalProperties:
                      type: string
                    type: object
                  priorityClassName:
                    type: string
                  replicas:
                    format: int32
                    type: integer
                  resources:
                    description: ResourceRequirements describes the compute resource
                      requirements.
                    properties:
                      limits:
                        additionalProperties:
                          anyOf:
                          - type: integer
                          - type: string
                          pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                          x-kubernetes-int-or-string: true
                        description: 'Limits describes the maximum amount of compute
                          resources allowed. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                        type: object
                      requests:
                        additionalProperties:
                          anyOf:
                          - type: integer
                          - type: string
                          pattern: ^(\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\+|-)?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))))?$
                          x-kubernetes-int-or-string: true
                        description: 'Requests describes the minimum amount of compute
                          resources required. If Requests is omitted for a container,
                          it defaults to Limits if that is explicitly specified, otherwise
                          to an implementation-defined value. More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/'
                        type: object
                    type: object
                  securityContext:
                    description: PodSecurityContext holds pod-level security attributes
                      and common container settings. Some fields are also present
                      in container.securityContext.  Field values of container.securityContext
                      take precedence over field values of PodSecurityContext.
                    properties:
                      fsGroup:
                        description: "A special supplemental group that applies to
                          all containers in a pod. Some volume types allow the Kubelet
                          to change the ownership of that volume to be owned by the
                          pod: \n 1. The owning GID will be the FSGroup 2. The setgid
                          bit is set (new files created in the volume will be owned
                          by FSGroup) 3. The permission bits are OR'd with rw-rw----
                          \n If unset, the Kubelet will not modify the ownership and
                          permissions of any volume."
                        format: int64
                        type: integer
                      fsGroupChangePolicy:
                        description: 'fsGroupChangePolicy defines behavior of changing
                          ownership and permission of the volume before being exposed
                          inside Pod. This field will only apply to volume types which
                          support fsGroup based ownership(and permissions). It will
                          have no effect on ephemeral volume types such as: secret,
                          configmaps and emptydir. Valid values are "OnRootMismatch"
                          and "Always". If not specified, "Always" is used.'
                        type: string
                      runAsGroup:
                        description: The GID to run the entrypoint of the container
                          process. Uses runtime default if unset. May also be set
                          in SecurityContext.  If set in both SecurityContext and
                          PodSecurityContext, the value specified in SecurityContext
                          takes precedence for that container.
                        format: int64
                        type: integer
                      runAsNonRoot:
                        description: Indicates that the container must run as a non-root
                          user. If true, the Kubelet will validate the image at runtime
                          to ensure that it does not run as UID 0 (root) and fail
                          to start the container if it does. If unset or false, no
                          such validation will be performed. May also be set in SecurityContext.  If
                          set in both SecurityContext and PodSecurityContext, the
                          value specified in SecurityContext takes precedence.
                        type: boolean
                      runAsUser:
                        description: The UID to run the entrypoint of the container
                          process. Defaults to user specified in image metadata if
                          unspecified. May also be set in SecurityContext.  If set
                          in both SecurityContext and PodSecurityContext, the value
                          specified in SecurityContext takes precedence for that container.
                        format: int64
                        type: integer
                      seLinuxOptions:
                        description: The SELinux context to be applied to all containers.
                          If unspecified, the container runtime will allocate a random
                          SELinux context for each container.  May also be set in
                          SecurityContext.  If set in both SecurityContext and PodSecurityContext,
                          the value specified in SecurityContext takes precedence
                          for that container.
                        properties:
                          level:
                            description: Level is SELinux level label that applies
                              to the container.
                            type: string
                          role:
                            description: Role is a SELinux role label that applies
                              to the container.
                            type: string
                          type:
                            description: Type is a SELinux type label that applies
                              to the container.
                            type: string
                          user:
                            description: User is a SELinux user label that applies
                              to the container.
                            type: string
                        type: object
                      seccompProfile:
                        description: The seccomp options to use by the containers
                          in this pod.
                        properties:
                          localhostProfile:
                            description: localhostProfile indicates a profile defined
                              in a file on the node should be used. The profile must
                              be preconfigured on the node to work. Must be a descending
                              path, relative to the kubelet's configured seccomp profile
                              location. Must only be set if type is "Localhost".
                            type: string
                          type:
                            description: "type indicates which kind of seccomp profile
                              will be applied. Valid options are: \n Localhost - a
                              profile defined in a file on the node should be used.
                              RuntimeDefault - the container runtime default profile
                              should be used. Unconfined - no profile should be applied."
                            type: string
                        required:
                        - type
                        type: object
                      supplementalGroups:
                        description: A list of groups applied to the first process
                          run in each container, in addition to the container's primary
                          GID.  If unspecified, no groups will be added to any container.
                        items:
                          format: int64
                          type: integer
                        type: array
                      sysctls:
                        description: Sysctls hold a list of namespaced sysctls used
                          for the pod. Pods with unsupported sysctls (by the container
                          runtime) might fail to launch.
                        items:
                          description: Sysctl defines a kernel parameter to be set
                          properties:
                            name:
                              description: Name of a property to set
                              type: string
                            value:
                              description: Value of a property to set
                              type: string
                          required:
                          - name
                          - value
                          type: object
                        type: array
                      windowsOptions:
                        description: The Windows specific settings applied to all
                          containers. If unspecified, the options within a container's
                          SecurityContext will be used. If set in both SecurityContext
                          and PodSecurityContext, the value specified in SecurityContext
                          takes precedence.
                        properties:
                          gmsaCredentialSpec:
                            description: GMSACredentialSpec is where the GMSA admission
                              webhook (https://github.com/kubernetes-sigs/windows-gmsa)
                              inlines the contents of the GMSA credential spec named
                              by the GMSACredentialSpecName field.
                            type: string
                          gmsaCredentialSpecName:
                            description: GMSACredentialSpecName is the name of the
                              GMSA credential spec to use.
                            type: string
                          hostProcess:
                            description: HostProcess determines if a container should
                              be run as a 'Host Process' container. This field is
                              alpha-level and will only be honored by components that
                              enable the WindowsHostProcessContainers feature flag.
                              Setting this field without the feature flag will result
                              in errors when validating the Pod. All of a Pod's containers
                              must have the same effective HostProcess value (it is
                              not allowed to have a mix of HostProcess containers
                              and non-HostProcess containers).  In addition, if HostProcess
                              is true then HostNetwork must also be set to true.
                            type: boolean
                          runAsUserName:
                            description: The UserName in Windows to run the entrypoint
                              of the container process. Defaults to the user specified
                              in image metadata if unspecified. May also be set in
                              PodSecurityContext. If set in both SecurityContext and
                              PodSecurityContext, the value specified in SecurityContext
                              takes precedence.
                            type: string
                        type: object
                    type: object
                  serviceAccountName:
                    type: string
                  serviceAnnotations:
                    additionalProperties:
                      type: string
                    type: object
                  tolerations:
                    items:
                      description: The pod this Toleration is attached to tolerates
                        any taint that matches the triple <key,value,effect> using
                        the matching operator <operator>.
                      properties:
                        effect:
                          description: Effect indicates the taint effect to match.
                            Empty means match all taint effects. When specified, allowed
                            values are NoSchedule, PreferNoSchedule and NoExecute.
                          type: string
                        key:
                          description: Key is the taint key that the toleration applies
                            to. Empty means match all taint keys. If the key is empty,
                            operator must be Exists; this combination means to match
                            all values and all keys.
                          type: string
                        operator:
                          description: Operator represents a key's relationship to
                            the value. Valid operators are Exists and Equal. Defaults
                            to Equal. Exists is equivalent to wildcard for value,
                            so that a pod can tolerate all taints of a particular
                            category.
                          type: string
                        tolerationSeconds:
                          description: TolerationSeconds represents the period of
                            time the toleration (which must be of effect NoExecute,
                            otherwise this field is ignored) tolerates the taint.
                            By default, it is not set, which means tolerate the taint
                            forever (do not evict). Zero and negative values will
                            be treated as 0 (evict immediately) by the system.
                          format: int64
                          type: integer
                        value:
                          description: Value is the taint value the toleration matches
                            to. If the operator is Exists, the value should be empty,
                            otherwise just a regular string.
                          type: string
                      type: object
                    type: array
                type: object
            type: object
        required:
        - spec
        type: object
    served: true
    storage: true
    subresources: {}
status:
  acceptedNames:
    kind: ""
    plural: ""
  conditions: []
  storedVersions: []