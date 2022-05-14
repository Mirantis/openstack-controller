from openstack_controller import utils
from jinja2.exceptions import TemplateRuntimeError


def substitute_local_proxy_hostname(url, hostname):
    return utils.substitute_local_proxy_hostname(url, hostname)


def raise_error(msg):
    raise TemplateRuntimeError(msg)
