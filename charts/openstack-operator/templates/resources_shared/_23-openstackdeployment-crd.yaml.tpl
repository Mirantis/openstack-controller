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
                  default: false
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
                    - victoria # LTS version
                    - wallaby # not supported, only for migration
                    - xena # not supported, only for migration
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
                    - single
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
                nodes:
                  type: object
                  # NOTE(vsaienko): the schema is validated by admission controller
                  description: Object that describes node specific overrides.
                  x-kubernetes-preserve-unknown-fields: true
                features:
                  type: object
                  required:
                    - ssl
                    - neutron
                    - nova
                  properties:
                    policies:
                      type: object
                      properties:
                        aodh: &custom_policies
                          type: object
                          x-kubernetes-preserve-unknown-fields: true
                          description: Values of policies to override.
                        barbican:
                          <<: *custom_policies
                        cinder:
                          <<: *custom_policies
                        designate:
                          <<: *custom_policies
                        glance:
                          <<: *custom_policies
                        gnocchi:
                          <<: *custom_policies
                        heat:
                          <<: *custom_policies
                        ironic:
                          <<: *custom_policies
                        keystone:
                          <<: *custom_policies
                        masakari:
                          <<: *custom_policies
                        neutron:
                          <<: *custom_policies
                        nova:
                          <<: *custom_policies
                        octavia:
                          <<: *custom_policies
                        panko:
                          <<: *custom_policies
                        placement:
                          <<: *custom_policies
                    glance:
                      type: object
                      properties:
                        backends:
                          description: |
                            Set of backeds are going to be used by glance as multi backends.
                          type: object
                          properties:
                            cinder:
                              type: object
                              x-kubernetes-preserve-unknown-fields: true
                              description: |
                                Section to configure cinder backends.
                            rbd:
                              type: object
                              x-kubernetes-preserve-unknown-fields: true
                              description: |
                                Section to configure rbd (Ceph) backends
                        signature:
                          type: object
                          properties:
                            enabled:
                              type: boolean
                              description: |
                                Enforce signature validation for images on upload. Upload of images without signature
                                metadata is rejected. When image signature is not valid compute service will not allow
                                to start instance and block storage service will not allow to create volumes.
                            certificate_validation:
                              type: boolean
                              description: Enable certificate validation when verifying signatures.
                    database:
                      type: object
                      properties:
                        cleanup:
                          type: object
                          properties:
                            barbican:
                              type: object
                              required:
                                - enabled
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable periodic cleanup of database for Barbican.
                                schedule:
                                  type: string
                                  description: Cron schedule for periodic cleanup.
                                age:
                                  type: integer
                                  description: |
                                    Number of days to keep deleted entries. When set to 0 all entries from shadow tables
                                    are deleted.
                            masakari:
                              type: object
                              required:
                                - enabled
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable periodic cleanup of database for Masakari.
                                schedule:
                                  type: string
                                  description: Cron schedule for periodic cleanup.
                                age:
                                  type: integer
                                  description: |
                                    Number of days to keep deleted entries. When set to 0 all entries from shadow tables
                                    are deleted.
                                batch:
                                  type: integer
                                  description: The batch size for each iteration.
                            nova:
                              type: object
                              required:
                                - enabled
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable periodic cleanup of database for Nova.
                                schedule:
                                  type: string
                                  description: Cron schedule for periodic cleanup.
                                age:
                                  type: integer
                                  description: |
                                    Number of days to keep deleted entries. When set to 0 all entries from shadow tables
                                    are deleted.
                                batch:
                                  type: integer
                                  description: The batch size for each iteration.
                            cinder:
                              type: object
                              required:
                                - enabled
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable periodic cleanup of database for Cinder.
                                schedule:
                                  type: string
                                  description: Cron schedule for periodic cleanup.
                                age:
                                  type: integer
                                  description: |
                                    Number of days to keep deleted entries. When set to 0 all entries from shadow tables
                                    are deleted.
                            glance:
                              type: object
                              required:
                                - enabled
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable periodic cleanup of database for Glance.
                                schedule:
                                  type: string
                                  description: Cron schedule for periodic cleanup.
                                age:
                                  type: integer
                                  description: |
                                    Number of days to keep deleted entries. When set to 0 all entries from shadow tables
                                    are deleted.
                                batch:
                                  type: integer
                                  description: The batch size for each iteration.
                            heat:
                              type: object
                              required:
                                - enabled
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable periodic cleanup of database for Heat.
                                schedule:
                                  type: string
                                  description: Cron schedule for periodic cleanup.
                                age:
                                  type: integer
                                  description: |
                                    Number of days to keep deleted entries. When set to 0 all entries from shadow tables
                                    are deleted.
                                batch:
                                  type: integer
                                  description: Number of stacks to delete at a time (per transaction).
                            aodh:
                              type: object
                              required:
                                - enabled
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable periodic cleanup of expired alarm history data for Aodh
                                schedule:
                                  type: string
                                  description: Cron schedule for periodic cleanup
                                age:
                                  type: integer
                                  description: |
                                    Number of days that alarm histories are kept in the database for (<= 0 means forever)
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
                    designate:
                      type: object
                      required:
                        - backend
                      properties:
                        backend:
                          type: object
                          required:
                            - type
                            - protocol
                          properties:
                            type:
                              default: powerdns
                              type: string
                              description: >
                                Type of the backend for Designate. For example: powerdns.
                            protocol:
                              type: string
                              default: udp
                              description: >
                                Protocol for Designate backend in Kubernetes Service. Could be udp|tcp|tcp+udp.
                              enum:
                                - udp
                                - tcp
                                - tcp+udp
                            external_ip:
                              description: >
                                Optional field to define IP address for LoadBalancer service.
                              type: string
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
                                namespace:
                                  description: >
                                    Vault Namespace to use for all requests to Vault.
                                    This is available only in Vault Enterprise and
                                    is supported only since OpenStack Victoria release.
                                  type: string
                                kv_mountpoint:
                                  description: >
                                    Mountpoint of KV store in Vault to use.
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
                          - stepler
                          - baremetal
                          - redis
                          - alarming
                          - event
                          - metering
                          - metric
                          - instance-ha
                    nova:
                      type: object
                      required:
                        - live_migration_interface
                      properties:
                        live_migration_interface:
                          type: string
                          description: "Physical interface used for live migration."
                        vcpu_type:
                          type: string
                          default: "host-model"
                          description: >
                            Types of cpu to create instances with. Can be host-model, host-passthrough
                            or a coma-separated list of qemu cpu types.
                            For OpenStack Stein and older, only single value can be provided.
                            Default is "host-model" for a optimal compromise between performance
                            and live-migration support.
                        images:
                          type: object
                          properties:
                            backend:
                              description: >
                                Backend for nova images can be ceph or local
                              type: string
                              enum:
                                - local
                                - ceph
                                - lvm
                            encryption:
                              type: object
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable ephemeral disk encryption, only available with lvm backend.
                                cipher:
                                  type: string
                                  description: Cipher-mode string to be used.
                                key_size:
                                  type: integer
                                  description: Encryption key length in bits.
                            lvm:
                              type: object
                              properties:
                                volume_group:
                                  type: string
                                  description: >
                                    Volume group used when images backend is lvm. Default to nova-vol
                    horizon:
                      type: object
                      properties:
                        default_theme:
                          type: string
                          description: The default theme name.
                        themes:
                          type: array
                          items:
                            type: object
                            required:
                              - name
                              - url
                              - sha256summ
                              - description
                            properties:
                              name:
                                type: string
                                description: Custom theme name
                              url:
                                type: string
                                description: Link to archive with theme
                              sha256summ:
                                type: string
                                description: The sha256 checksumm of arhive with theme
                              description:
                                type: string
                                description: Theme description showed to user
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
                                OIDCRedirectURLsAllowed:
                                  type: string
                                  description: >
                                    Define one or more regular expressions that specify URLs (or domains) allowed for post logout and
                                    other redirects such as the "return_to" value on refresh token requests
                                OIDCScope:
                                   type: string
                                   description: Used to request specific scopes
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
                                required:
                                - enabled
                                - name
                                - config
                                properties:
                                  enabled:
                                    type: boolean
                                    description: Enable domain specific keystone configuration
                                  name:
                                    type: string
                                    description: Domain name
                                  config:
                                    x-kubernetes-preserve-unknown-fields: true
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
                          type: object
                          required:
                            - enabled
                          properties:
                            enabled:
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
                            network_type:
                              type: string
                              enum:
                                - flat
                                - vlan
                              description: network physical mechanism
                            segmentation_id:
                              type: integer
                              description: vlan id for vlan networks
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
                                        x-kubernetes-preserve-unknown-fields: true
                                        type: object
                                        description: RAW config for device.
                        bgpvpn:
                          type: object
                          required:
                            - enabled
                            - as_number
                          properties:
                            enabled:
                              type: boolean
                              description: Enable BGPVPN plugin/service
                            control_interface:
                              type: string
                              description: IP address or interface used for BGP peerings
                            dataplane_interface:
                              type: string
                              description: IP address or interface used to send VPN traffic
                            peers:
                              type: array
                              description: IP addresses of BGP peers, when not specified will be picked from secret
                              items:
                                type: string
                            as_number:
                              type: integer
                              description: Autonomous System number
                            evpn_vxlan_port:
                              type: integer
                              description: UDP port toward which send VXLAN traffic
                            route_reflector:
                              type: object
                              description: The object describes RouteReflector settings
                              properties:
                                enabled:
                                  type: boolean
                                  description: Enable BGPVPN route reflector on controller nodes
                                neighbor_subnets:
                                  type: array
                                  description: BGP sessions allowed from neighbors in this subnet
                                  items:
                                    type: string
                        ipsec:
                          type: object
                          required:
                            - enabled
                          properties:
                            enabled:
                              type: boolean
                              description: Enable IPsec authentication and encryption of tenant traffic
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
                              - baremetal
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
                      properties:
                        enabled:
                          description: >
                            enable StackLight operations support system
                          type: boolean
                        user:
                          type: object
                          properties:
                            username:
                              type: string
                              description: >
                                The option is no longer handled, the username is autogenerated.
                            password:
                              type: string
                              description: >
                                The option is no longer handled, the password is autogenerated.
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
                        masakari:
                          <<: *logging_level
                        barbican:
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
            status:
              x-kubernetes-preserve-unknown-fields: true
              type: object
              description: this is arbitrary JSON
              properties:
                watched:
                  type: object
                  description: >
                    The object that contains information of objects that openstack-controller
                    is watching for. Changin fields of this object will trigger update of
                    all children.
                  properties:
                    ceph:
                      type: object
                      properties:
                        secret:
                          type: object
                          properties:
                            hash:
                              type: string
                              description: >
                                The hash value for secret, is a trigger to reload ceph
                                metadata
                    neutron:
                      properties:
                        bgpvpn_neighbor_secret:
                          properties:
                            hash:
                              description: |
                                The hash value for secret, is a trigger to reload neutron bgpvpn metadata
                              type: string
                          type: object
                      type: object
      additionalPrinterColumns:
      - name: OpenStack
        type: string
        description: OpenStack release
        jsonPath: .spec.openstack_version
      - name: Age
        type: date
        jsonPath: .metadata.creationTimestamp
      - name: Draft
        type: boolean
        jsonPath: .spec.draft
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
