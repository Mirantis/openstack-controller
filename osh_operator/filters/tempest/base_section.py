import abc
import jsonpath_rw as jsonpath


class BaseSection(object):
    def __init__(self, spec, helmbundles_body):
        super(BaseSection, self).__init__()
        self.spec = spec
        self.helmbundles_body = helmbundles_body

    @abc.abstractproperty
    def name(self):
        """"""

    @abc.abstractproperty
    def options():
        """"""

    def get_config_item(self, service_name, item_path, item_default=None):
        for component_name, component in self.helmbundles_body.items():
            for release in component.get("spec", {}).get("releases", []):
                chart_name = release["chart"].split("/")[-1]
                if chart_name == service_name:
                    res = jsonpath.parse(item_path).find(
                        release["values"]["conf"]
                    )
                    if res:
                        return res[0].value
                    else:
                        return item_default
