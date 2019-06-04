import kopf


@kopf.on.create('lcm.miratis.com', 'v1alpha1', 'openstackdeployments')
def deploy(body, spec, **kwargs):
    print(f"And here we are! Creating: {spec}")
    return {'message': 'hello world'}  # will be the new status
