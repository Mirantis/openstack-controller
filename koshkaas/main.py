import kopf


@kopf.on.create('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def create_fn(body, spec, **kwargs):
    print(f"And here we are! Creating: {spec}")
    return {'message': 'hello world'}  # will be the new status


@kopf.on.update('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def update_fn(body, spec, **kwargs):
    print(f"And here we are! Creating: {spec}")
    return {'message': 'new world'}  # will be the new status


@kopf.on.delete_fn('lcm.mirantis.com', 'v1alpha1', 'openstackdeployments')
async def delete(body, spec, **kwargs):
    print(f"And here we are! Creating: {spec}")
    return {'message': 'by world'}  # will be the new status
