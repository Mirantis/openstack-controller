import logging

from kombu import Connection
from unittest import TestCase

from openstack_controller import kube
from openstack_controller import openstack_utils

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "aiohttp": {
            "level": "WARNING",
        },
        "stevedore": {
            "level": "INFO",
        },
        "urllib3": {
            "level": "INFO",
        },
    },
    "root": {
        "handlers": ["default"],
        "level": "DEBUG",
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logging_old_factory = logging.getLogRecordFactory()
LOG = logging.getLogger(__name__)


class BaseFunctionalTestCase(TestCase):
    def setUp(self):
        self.kube_api = kube.kube_client()
        self.ocm = openstack_utils.OpenStackClientManager()
        self.osdpl = kube.get_osdpl()
        self.setup_logging()

    def setup_logging(self):
        logging.setLogRecordFactory(self.logging_record_factory)

    def logging_record_factory(self, *args, **kwargs):
        record = logging_old_factory(*args, **kwargs)
        record.testMethodName = self._testMethodName
        return record

    def is_service_enabled(self, name):
        return name in self.osdpl.obj["spec"].get("features", {}).get(
            "services", []
        )

    def check_rabbitmq_connection(
        self, username, password, host, port, vhost, ssl=False
    ):
        rabbitmq_url = f"amqp://{username}:{password}@{host}:{port}/{vhost}"
        connection = Connection(rabbitmq_url, ssl=ssl)
        try:
            LOG.info(f"Connecting to the: {rabbitmq_url}")
            connection.ensure_connection(max_retries=3)
            connection.channel()
            return True
        except Exception as e:
            LOG.error(f"Connection error. Error: {e}")
        finally:
            connection.release()
