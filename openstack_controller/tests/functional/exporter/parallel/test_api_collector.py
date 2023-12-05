from openstack_controller.tests.functional.exporter import base


class APICollectorFunctionalTestCase(base.BaseFunctionalExporterTestCase):
    known_metrics = {
        "osdpl_api_success": {
            "labels": ["service_name", "service_type", "url"]
        },
        "osdpl_api_latency": {
            "labels": ["service_name", "service_type", "url"]
        },
        "osdpl_api_status": {
            "labels": ["service_name", "service_type", "url"]
        },
    }
