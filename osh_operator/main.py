import kopf
import kubernetes
import os
import pathlib
import yaml


@kopf.on.create('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def create(body, spec, logger, **kwargs):
    root_templates = '/opt/osh_operator'
    if os.getenv('OSH_OPERATOR_DEV', None):
        root_templates = __file__
    p = pathlib.Path(
        root_templates).parent / 'templates' / 'stein' / 'ingress.yaml'
    with p.open() as f:
        data = yaml.safe_load(f)
    data['spec']['repositories'] = spec['common']['charts']['repositories']

    kopf.adopt(data, body)

    api = kubernetes.client.CustomObjectsApi()
    obj = api.create_namespaced_custom_object('lcm.mirantis.com',
                                              'v1alpha1', 'default',
                                              'helmbundles',
                                              body=data)

    logger.info(f"HelmBundle child is created: %s", obj)
    return {'message': 'created!'}


@kopf.on.update('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def update(body, spec, **kwargs):
    print(f"And here we are! Creating: {spec}")
    return {'message': 'new world'}  # will be the new status


@kopf.on.delete('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def delete(meta, logger, **kwargs):
    logger.info(f"deleting {meta['name']}")
    return {'message': 'by world'}
