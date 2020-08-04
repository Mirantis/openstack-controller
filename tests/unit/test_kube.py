import pykube

from openstack_controller import kube


def test_get_kubernetes_objects():
    kube_objects = kube.get_kubernetes_objects()
    assert kube_objects[("v1", "Secret")] == kube.Secret
    assert kube_objects[("v1", "Namespace")] == pykube.objects.Namespace
