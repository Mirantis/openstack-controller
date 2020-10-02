apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  # name must match the spec fields below, and be in the form: <plural>.<group>
  name: openstackdeployments.lcm.mirantis.com
spec:
  # group name to use for REST API: /apis/<group>/<version>
  group: lcm.mirantis.com
  # list of versions supported by this CustomResourceDefinition
  versions:
    - name: v1alpha1
      # Each version can be enabled/disabled by Served flag.
      served: true
      # One and only one version must be marked as the storage version.
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            apiVersion:
              type: string
            kind:
              type: string
            metadata:
              type: object
            spec:
              type: object
              properties:
                draft:
                  type: boolean
                  description: trigger to process osdpl resource
                artifacts:
                  type: object
                  properties:
                    images_base_url:
                      type: string
                      description: "base URL for docker images"
                    binary_base_url:
                      type: string
                      description: "base URL for repo with helm charts & other binaries"
                openstack_version:
                  description: version of OpenStack to deploy
                  type: string
                  enum:
                    - queens # not supported, only for migration
                    - rocky # not supported, only for migration
                    - stein # not supported, only for migration
                    - train # not supported, only for migration
                    - ussuri # production version
                    - master # not supported, only for example
                preset:
                  description: Preset of features to deploy
                  type: string
                  enum:
                    - compute
                    - compute-tf
                size:
                  description: timeout and sizing parameters
                  type: string
                  enum:
                    - tiny
                    - small
                    - medium
                public_domain_name:
                  type: string
                  description: domain name used for public endpoints
                internal_domain_name:
                  type: string
                  description: internal k8s domain name
                local_volume_storage_class:
                  type: string
                  description: >
                    Default storage class with local volumes, used by services with built in clustering
                    mechanism like mariadb, etcd, redis.
                persistent_volume_storage_class:
                  type: string
                  description: >
                    Default storage class with persistence, for example ceph. Used by services that require
                    persistence on filesystem level like backups for mariadb.
                common:
                  type: object
                  properties:
                    charts:
                      type: object
                      description: settings passed to every helm chart
                      properties:
                        releases:
                          type: object
                          properties:
                            values:
                              type: object
                        repositories:
                          type: array
                          description: list of helm chart repositories
                          items:
                            type: object
                            properties:
                              name:
                                type: string
                                description: symbolic name to reference this repo
                              url:
                                type: string
                                description: helm charts repo url
                            required:
                              - name
                              - url
                        values:
                          x-kubernetes-preserve-unknown-fields: true
                          type: object
                          description: JSON of values passed to all charts
                    infra:
                      type: object
                      properties:
                        releases:
                          type: object
                          properties:
                            version:
                              type: string
                              description: version of charts to install for infra components
                        repo:
                          type: string
                        values:
                          x-kubernetes-preserve-unknown-fields: true
                          type: object
                          description: JSON of values passed to all infra charts
                    openstack:
                      type: object
                      properties:
                        releases:
                          type: object
                          properties:
                            version:
                              type: string
                              description: version of charts to install for openstack components
                        repo:
                          type: string
                        values:
                          x-kubernetes-preserve-unknown-fields: true
                          type: object
                          description: JSON of values passed to all openstack charts
                features:
                  type: object
                  required:
                    - ssl
                    - neutron
                    - nova
                  properties:
                    database:
                      type: object
                      properties:
                        backup:
                          type: object
                          required:
                            - enabled
                          properties:
                            enabled:
                              description: >
                                Indicates whether cron job will launch backup jobs. When set to true suspend
                                flag in cron job will be switched to false.
                              type: boolean
                            schedule_time:
                              description: >
                                Unix style cron expression indicates how often to run backup
                                cron job. Default is '0 1 * * *' - every day at 01:00.
                              type: string
                            backup_type:
                              description: >
                                Type of backup. Possible values: incremental or full.
                                incremental: If newest full backup is older then full_backup_cycle seconds,
                                perform full backup, else perform incremental backup to the newest full.
                                full: perform always only full backup. Default is incremental.
                              type: string
                            backups_to_keep:
                              description: >
                                How many full backups to keep.
                              type: integer
                            full_backup_cycle:
                              description: >
                                Number of seconds that defines a period between 2 full backups.
                                During this period incremental backups will be performed. The parameter
                                is taken into account only if backup_type is set to 'incremental', otherwise
                                it is ignored. For example with full_backup_cycle set to 604800 seconds full
                                backup will be taken every week and if cron is set to 0 0 * * *, incremental backup
                                will be performed on daily basis.
                              type: integer
                    telemetry:
                      type: object
                      required:
                       - mode
                      properties:
                        mode:
                          type: string
                          enum:
                            - autoscaling
                          description: >
                            Which telemetry mode is going to be used for telemetry.
                    ssl:
                      type: object
                      required:
                       - public_endpoints
                      properties:
                        public_endpoints:
                          type: object
                          required:
                            - ca_cert
                            - api_cert
                            - api_key
                          properties:
                            ca_cert:
                              description: >
                                CA certificate
                              type: string
                            api_cert:
                              description: >
                                API server certificate
                              type: string
                            api_key:
                              description: >
                                API server private key
                              type: string
                    barbican:
                      type: object
                      properties:
                        backends:
                          type: object
                          properties:
                            vault:
                              type: object
                              properties:
                                enabled:
                                  description: >
                                    Indicates if simple_crypto backend is enabled
                                  type: boolean
                                approle_role_id:
                                  description: >
                                    Specifies the app role ID
                                  type: string
                                approle_secret_id:
                                  description: >
                                     Specifies the secret ID created for the app role
                                  type: string
                                vault_url:
                                  description: >
                                    URL of the Vault server
                                  type: string
                                use_ssl:
                                  description: >
                                    Specifies whether to use SSL
                                  type: boolean
                                ssl_ca_crt_file:
                                  description: >
                                    The path to CA cert file
                                  type: string
                    services:
                      type: array
                      description: List of enabled openstack and auxiliary services
                      items:
                        type: string
                        enum:
                          - block-storage
                          - compute
                          - identity
                          - dashboard
                          - image
                          - ingress
                          - database
                          - memcached
                          - networking
                          - orchestration
                          - object-storage
                          - messaging
                          - tempest
                          - load-balancer
                          - dns
                          - key-manager
                          - placement
                          - coordination
                          - dashboard-selenium
                          - baremetal
                          - redis
                          - alarming
                          - event
                          - metering
                          - metric
                    nova:
                      type: object
                      required:
                        - live_migration_interface
                      properties:
                        live_migration_interface:
                          type: string
                          description: "Physical interface used for live migration."
                        images:
                          type: object
                          properties:
                            backend:
                              description: >
                                backend for nova images can be ceph or local
                              type: string
                              enum:
                                - local
                                - ceph
                    keystone:
                      type: object
                      properties:
                        users:
                          type: object
                          properties:
                            admin:
                              type: object
                              properties:
                                region_name:
                                  description: >
                                    OpenStack region name
                                  type: string
                                project_name:
                                  description: >
                                    Project name for admin of OpenStack deployment
                                  type: string
                                user_domain_name:
                                  description: >
                                    Domain name for admin of OpenStack deployment
                                  type: string
                                project_domain_name:
                                  description: >
                                    Project domain name for admin of OpenStack deployment
                                  type: string
                                default_domain_id:
                                  description: >
                                    Domain ID for admin of OpenStack deployment
                                  type: string
                        keycloak:
                          type: object
                          properties:
                            enabled:
                              description: Trigger to enable keycloak integration
                              type: boolean
                            url:
                              type: string
                              description: Url for keycloak
                            oidc:
                              type: object
                              properties:
                                OIDCClientID:
                                  type: string
                                  description: Client identifier used in calls to the statically configured OpenID Connect Provider
                                OIDCProviderMetadataURL:
                                  type: string
                                  description: Override for URL where OpenID Connect Provider metadata can be found
                                OIDCRedirectURI:
                                  type: array
                                  description: The redirect_uri for this OpenID Connect client
                                  items:
                                    type: string
                                OIDCSSLValidateServer:
                                  type: boolean
                                  description: Require a valid SSL server certificate when communicating with the OP
                                OIDCOAuthSSLValidateServer:
                                  type: boolean
                                  description: Require a valid SSL server certificate when communicating with the Authorization Server
                        domain_specific_configuration:
                          type: object
                          properties:
                            enabled:
                              type: boolean
                              description: Enable domain specific keystone configuration
                            domains:
                              type: array
                              description: >
                                The list of domain specific configuration options.
                              items:
                                type: object
                                properties:
                                  enabled:
                                    type: boolean
                                    description: Enable domain specific keystone configuration
                                  name:
                                    type: string
                                    description: Domain name
                                  config:
                                    type: object
                                    description: Domain specific configuration options.
                    neutron:
                      type: object
                      required:
                        - tunnel_interface
                      properties:
                        tunnel_interface:
                          type: string
                          description: "Physical interface used for tunnel traffic"
                        dns_servers:
                          type: array
                          description: >
                            The list with the IP addresses of DNS servers reachable from Virtual Networks
                          items:
                            type: string
                        backend:
                          type: string
                          description: Neutron backend
                          enum:
                            - ml2
                            - tungstenfabric
                        dvr:
                          type: boolean
                          description: Enable distributed routers
                        tenant_network_types:
                          type: array
                          description: Ordered list of network_types to allocate as tenant networks
                          items:
                            type: string
                            enum:
                              - flat
                              - vlan
                              - vxlan
                        external_networks:
                          type: array
                          items:
                            type: object
                            required:
                              - physnet
                              - bridge
                              - network_types
                            properties:
                              physnet:
                                type: string
                                description: Neutron physnet name
                              interface:
                                type: string
                                description: Physical interface mapped with physnet
                              bridge:
                                type: string
                                description: OVS bridge name to map with physnet.
                              network_types:
                                type: array
                                description: Network types allowed on particular physnet
                                items:
                                  type: string
                                  enum:
                                    - flat
                                    - vlan
                                    - vxlan
                                    - gre
                                    - local
                              vlan_ranges:
                                type: string
                                nullable: true
                                description: Range of vlans allowed on physnet
                              mtu:
                                type: integer
                                nullable: true
                        floating_network:
                          type: object
                          properties:
                            enabled:
                              type: boolean
                              description: >
                                enable floating network creation
                            name:
                              type: string
                              description: The name of floating network
                            physnet:
                              type: string
                              description: >
                                name of physical network to associate
                            subnet:
                              type: object
                              required:
                                - range
                                - pool_start
                                - pool_end
                                - gateway
                              properties:
                                name:
                                  type: string
                                  description: "The name of floating subnet"
                                range:
                                  type: string
                                  description: "IP address range ie: 1.2.3.0/24"
                                pool_start:
                                  type: string
                                  description: "start IP address ie: 1.2.3.100"
                                pool_end:
                                  type: string
                                  description: "end IP address ie: 1.2.3.200"
                                gateway:
                                  type: string
                                  description: "IP address of subnet gateway"
                            router:
                              type: object
                              properties:
                                name:
                                  type: string
                                  description: "The name of public router"
                        baremetal:
                          type: object
                          properties:
                            ngs:
                              type: object
                              properties:
                                devices:
                                  type: array
                                  items:
                                    type: object
                                    required:
                                      - name
                                      - device_type
                                      - ip
                                      - username
                                    properties:
                                      name:
                                        type: string
                                        description: Switch name
                                      device_type:
                                        type: string
                                        description: Netmiko device type
                                      ip:
                                        type: string
                                        description: IP address of switch
                                      username:
                                        type: string
                                        description: Credential username
                                      password:
                                        type: string
                                        description: Credential password
                                      ssh_private_key:
                                        type: string
                                        description:  SSH private key for switch.
                                      secret:
                                        type: string
                                        description: Enable secret
                                      raw:
                                        type: object
                                        description: RAW config for device.
                    messaging:
                      type: object
                      properties:
                        components_with_dedicated_messaging:
                          type: array
                          description: "Array of components need to be set up with dedicated rabbitmq server for migration"
                          items:
                            type: string
                            enum:
                              - load-balancer
                              - dns
                              - key-manager
                              - block-storage
                              - orchestration
                              - compute
                              - image
                    ironic:
                      type: object
                      required:
                        - provisioning_interface
                        - baremetal_network_name
                        - networks
                      properties:
                        provisioning_interface:
                          type: string
                          description: name of physical interface to bind PXE services
                        baremetal_network_name:
                          type: string
                          description: name of baremetal provisioning/cleaning network
                        networks:
                          type: object
                          properties:
                            baremetal:
                              type: object
                              properties:
                                name:
                                  type: string
                                  description: name of baremetal network
                                physnet:
                                  type: string
                                  description: name of physical network to associate
                                network_type:
                                  type: string
                                  enum:
                                    - flat
                                    - vlan
                                  description: type of provisioning/cleaning baremetal network
                                segmentation_id:
                                  type: integer
                                  description: the vlan number of cleaning network in case of VLAN segmentation is used
                                mtu:
                                  type: integer
                                  description: the MTU for cleaning network
                                external:
                                  type: boolean
                                shared:
                                  type: boolean
                                subnets:
                                  type: array
                                  items:
                                    type: object
                                    required:
                                      - name
                                      - range
                                      - pool_start
                                      - pool_end
                                      - gateway
                                    properties:
                                      name:
                                        type: string
                                        description: baremetal subnet name
                                      range:
                                        type: string
                                        description: the cidr of baremetal network
                                      pool_start:
                                        type: string
                                        description: the start range of allocation pool for baremetal network
                                      pool_end:
                                        type: string
                                        description: the end range of allocation pool for baremetal network
                                      gateway:
                                        type: string
                                        description: the gateway for baremetal network
                        agent_images:
                          type: object
                          properties:
                            base_url:
                              description: base URL for ironic agent images
                              type: string
                            initramfs:
                              type: string
                            kernel:
                              type: string
                    octavia:
                      type: object
                      properties:
                        lb_network:
                          type: object
                          required:
                            - subnets
                          properties:
                            subnets:
                              type: array
                              items:
                                type: object
                                required:
                                  - range
                                  - pool_start
                                  - pool_end
                                properties:
                                  range:
                                    type: string
                                    description: "IP address range ie: 1.2.3.0/24"
                                  pool_start:
                                    type: string
                                    description: "start IP address ie: 1.2.3.100"
                                  pool_end:
                                    type: string
                                    description: "end IP address ie: 1.2.3.200"
                    stacklight:
                      type: object
                      required:
                        - user
                      properties:
                        enabled:
                          description: >
                            enable StackLight operations support system
                          type: boolean
                        user:
                          type: object
                          required:
                            - password
                          properties:
                            username:
                              type: string
                              description: >
                                Rabbitmq username to access notifications.
                            password:
                              type: string
                              description: >
                                Rabbitmq password to access notifications.
                    logging:
                      type: object
                      properties:
                        cinder: &logging_level
                          type: object
                          properties:
                            level:
                              type: string
                              description: Service logging level
                              enum:
                                - DEBUG
                                - INFO
                                - WARNING
                                - ERROR
                                - CRITICAL
                        designate:
                          <<: *logging_level
                        glance:
                          <<: *logging_level
                        heat:
                          <<: *logging_level
                        ironic:
                          <<: *logging_level
                        keystone:
                          <<: *logging_level
                        neutron:
                          <<: *logging_level
                        nova:
                          <<: *logging_level
                        octavia:
                          <<: *logging_level
                        aodh:
                          <<: *logging_level
                        panko:
                          <<: *logging_level
                        gnocchi:
                          <<: *logging_level
                        ceilometer:
                          <<: *logging_level
                migration:
                  x-kubernetes-preserve-unknown-fields: true
                  type: object
                  description: this is arbitrary JSON of parameters for migration
                services:
                  x-kubernetes-preserve-unknown-fields: true
                  type: object
                  description: this is arbitrary JSON
                timeouts:
                  type: object
                  properties:
                    application_readiness:
                      type: object
                      properties:
                        nova: &application_readiness
                          type: object
                          properties:
                            timeout:
                              type: integer
                              description: Number of seconds to wait for application becomes ready.
                            delay:
                              type: integer
                              description: Number of seconds between readiness attempts.
                        neutron:
                          <<: *application_readiness
              required:
                - openstack_version
                - preset
                - size
                - public_domain_name
                - internal_domain_name
            status:
              x-kubernetes-preserve-unknown-fields: true
              type: object
              description: this is arbitrary JSON
  # either Namespaced or Cluster
  scope: Namespaced
  names:
    # plural name to be used in the URL: /apis/<group>/<version>/<plural>
    plural: openstackdeployments
    # singular name to be used as an alias on the CLI and for display
    singular: openstackdeployment
    # kind is normally the CamelCased singular type. Your resource manifests use this.
    kind: OpenStackDeployment
    # shortNames allow shorter string to match your resource on the CLI
    shortNames:
      - osdpl
    categories:
      - all
  additionalPrinterColumns:
    - name: Age
      type: date
      JSONPath: .metadata.creationTimestamp
    - name: Deployed
      type: boolean
      JSONPath: .status.deployed
    - name: Draft
      type: boolean
      JSONPath: .spec.draft
