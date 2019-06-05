import kopf
import kubernetes
import yaml


@kopf.on.create('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def create(body, spec, logger, **kwargs):
    with open('/opt/operator/osh_operator/templates/stein/ingress.yaml') as f:
        data = yaml.safe_load(f)
    data['spec']['repositories'] = spec['common']['charts']['repositories']
    api = kubernetes.client.CustomObjectsApi()
    obj = api.create_namespaced_custom_object('lcm.mirantis.com',
                                              'v1alpha1', 'default',
                                              'helmbundles',
                                              body=data)
    kopf.adopt(obj, body)
    return {'message': 'created!'}


@kopf.on.update('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def update(body, spec, **kwargs):
    print(f"And here we are! Creating: {spec}")
    return {'message': 'new world'}  # will be the new status


@kopf.on.delete('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def delete(body, spec, **kwargs):
    print(f"And here we are! Creating: {spec}")
    return {'message': 'by world'}  # will be the new status
