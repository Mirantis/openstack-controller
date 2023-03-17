# List of know deployment issues

## Ceph volume might be failing to mounting to pod

In KaaS kubespray have non default value for FLEXVOLUME_DIR_PATH we need to either

  * Set this value explicitly in rook https://github.com/jumpojoy/os-k8s/blob/master/crds/helmbundle/ceph/rook.yaml#L20
  * Remove non default value from kubespray

## DNS resolving issue

Helm charts have default domain cluster.local in values.yaml. The domain is not added to list of default domains in
coredns:

  * Add cluster.local to list of default domains
    Edit `kubectl -n kube-system edit configmap coredns` and add `cluster.local.` to
    list of default domains. Redeploy pods to apply changes immidiately `kubectl delete  pods -n kube-system -l k8s-app=kube-dns`
  * Change default domain for deployment to actual value.
    `sed -i 's/#DNS=/DNS=10.233.0.3/g' /etc/systemd/resolved.conf`
    `systemctl restart systemd-resolved`