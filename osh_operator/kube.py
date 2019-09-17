import functools
import logging

import kopf
import pykube
from typing import Dict

log = logging.getLogger(__name__)


def login():
    try:
        # running in cluster
        config = pykube.KubeConfig.from_service_account()
    except FileNotFoundError:
        # not running in cluster => load local ~/.kube/config for testing
        config = pykube.KubeConfig.from_file()
    client = pykube.HTTPClient(config)
    log.info(f"Created k8s api client from context {config.current_context}")
    return client


api = login()


class OpenStackDeployment(pykube.objects.NamespacedAPIObject):
    version = "lcm.mirantis.com/v1alpha1"
    kind = "OpenStackDeployment"
    endpoint = "openstackdeployments"
    kopf_on_args = *version.split("/"), endpoint


def resource(data):
    return pykube.object_factory(api, data["apiVersion"], data["kind"])(
        api, data
    )


def find(klass, name, namespace=None):
    return klass.objects(api).filter(namespace=namespace).get(name=name)


def wait_for_resource(klass, name, namespace=None, delay=60):
    try:
        find(klass, name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        raise kopf.HandlerRetryError(
            f"The object: {klass.kind} is not found yet.", delay=delay
        )
    except:
        raise kopf.HandlerRetryError(
            f"Unknown error occured while getting object: {klass.kind}.",
            delay=delay,
        )


def wait_for_secret(namespace, name):
    wait_for_resource(pykube.Secret, name, namespace)


def save_secret_data(namespace: str, name: str, data: Dict[str, str]):
    secret = {"metadata": {"name": name, "namespace": namespace}, "data": data}
    try:
        find(pykube.Secret, name, namespace)
    except pykube.exceptions.ObjectDoesNotExist:
        pykube.Secret(api, secret).create()
    pykube.Secret(api, secret).update()


find_osdpl = functools.partial(find, OpenStackDeployment)
