import logging

from kombu import Connection
from unittest import TestCase

from openstack_controller import kube
from openstack_controller import openstack_utils
from openstack_controller.tests.functional import config as conf
from openstack_controller.tests.functional import data_utils, waiters

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
    @classmethod
    def setUpClass(cls):
        cls.ocm = openstack_utils.OpenStackClientManager()

    def setUp(self):
        self.kube_api = kube.kube_client()
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

    @classmethod
    def server_create(
        cls,
        wait=True,
        name=None,
        flavorRef=None,
        imageRef=None,
        networks="none",
    ):
        if name is None:
            name = data_utils.rand_name()
        if flavorRef is None:
            flavorRef = cls.ocm.oc.compute.find_flavor(conf.TEST_FLAVOR_NAME)
        if imageRef is None:
            imageRef = cls.ocm.oc.get_image_id(conf.CIRROS_TEST_IMAGE_NAME)

        server = cls.ocm.oc.compute.create_server(
            name=name,
            imageRef=imageRef,
            flavorRef=flavorRef.id,
            networks=networks,
            wait=wait,
        )
        if wait is True:
            waiters.wait_for_server_status(cls.ocm, server, status="ACTIVE")
        cls.addClassCleanup(cls.server_delete, server)
        return server

    @classmethod
    def server_delete(cls, server, wait=True):
        return cls.ocm.oc.delete_server(server.id, wait=wait)

    def server_reset_state(self, server, status, wait=True):
        self.ocm.oc.compute.reset_server_state(server.id, status)
        if wait is True:
            waiters.wait_for_server_status(self.ocm, server, status=status)
