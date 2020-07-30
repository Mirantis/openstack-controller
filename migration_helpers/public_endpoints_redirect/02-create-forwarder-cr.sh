#/bin/bash

RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$(cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common
. $TOP_DIR/database/functions

PORTS=$(openstack endpoint list --interface public -f value -c "URL" | sed -r 's/.*:([0-9]+).*/\1/' | sort | uniq)

cat << EOF > ${HELMBUNDLE_CR}
apiVersion: lcm.mirantis.com/v1alpha1
kind: HelmBundle
metadata:
  name: nginx-mcp1-forwarder
  namespace: ${HELMBUNDLE_NS}
spec:
  repositories:
  - name: nginx-forwarder
    url: https://artifactory.mcp.mirantis.net/binary-dev-kaas-local/kubernetes/helm/incubator
  releases:
  - name: mcp1-forwarder
    chart: nginx-forwarder/nginx
    version: 6.0.2
    namespace: ${FORWARDER_NS}
    values:
      extraVolumes:
        - name: public-endpoints-tls
          secret:
            secretName: public-endpoints-tls
            defaultMode: 0444
      extraVolumeMounts:
        - name: public-endpoints-tls
          mountPath: /opt/bitnami/nginx/conf/public-endpoints-tls.crt
          subPath: tls.crt
          readOnly: true
        - name: public-endpoints-tls
          mountPath: /opt/bitnami/nginx/conf/public-endpoints-tls.key
          subPath: tls.key
          readOnly: true
        - name: public-endpoints-tls
          mountPath: /opt/bitnami/nginx/conf/public-endpoints-tls_ca.key
          subPath: ca.crt
          readOnly: true
      cloneStaticSiteFromGit:
        enabled: false
      service:
        ports:
EOF

for port in $PORTS
do
cat << EOF >> ${HELMBUNDLE_CR}
          - name: $(get_service_by port ${port})
            port: ${port}
            protocol: TCP
EOF
done

cat << EOF >> ${HELMBUNDLE_CR}
      serverBlock: |-
        ssl_certificate     public-endpoints-tls.crt;
        ssl_certificate_key public-endpoints-tls.key;
EOF

for port in $PORTS
do
cat << EOF >> ${HELMBUNDLE_CR}
        server {
          listen 0.0.0.0:${port} ssl;
          location / {
            return 301 https://$(get_service_by port ${port}).${MCP2_PUBLIC_DOMAIN_NAME}\$request_uri;
          }
        }
EOF
done

