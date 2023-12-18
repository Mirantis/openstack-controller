from openstack_controller import constants
from openstack_controller import kube


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Config(metaclass=SingletonMeta):
    def __init__(self):
        self._osdpl = kube.get_osdpl()

        self.CIRROS_TEST_IMAGE_NAME = self.get_cirros_image()
        self.UBUNTU_TEST_IMAGE_NAME = "Ubuntu-18.04"
        self.TEST_FLAVOR_NAME = "m1.extra_tiny_test"
        self.TEST_SUBNET_RANGE = "10.20.30.0/24"
        self.PUBLIC_NETWORK_NAME = "public"

        # Time in seconds to wait for a compute operation to complete. Default is 120 seconds.
        self.COMPUTE_TIMEOUT = 60 * 2
        # Interval in seconds to check the status of a compute resource. Default is 1 second.
        self.COMPUTE_BUILD_INTERVAL = 1

        # Time in seconds to wait for a metric value. Default is 30 seconds.
        self.METRIC_TIMEOUT = 45
        # Interval in seconds to check the metric value. Default is 1 second.
        self.METRIC_INTERVAL_TIMEOUT = 5

        # Time in seconds to wait for a volume operation to complete. Default is 60 seconds.
        self.VOLUME_TIMEOUT = 30 * 2
        # Interval in seconds to check the status of a compute resource. Default is 1 second.
        self.VOLUME_BUILD_INTERVAL = 1

        # Time in seconds to wait for a server to change a status. Default is 30 seconds.
        self.SERVER_TIMEOUT = 30
        # Interval in seconds to check the server status. Default is 1 second.
        self.SERVER_READY_INTERVAL = 1

        # Time in seconds to wait for a volume create. Default is 30 seconds.
        self.VOLUME_TIMEOUT = 30
        # Interval in seconds to check the volume status. Default is 1 second.
        self.VOLUME_READY_INTERVAL = 1
        # Size, in GB of the volume to create.
        self.VOLUME_SIZE = 1

    def get_cirros_image(self):
        openstack_version = self._osdpl.obj["spec"]["openstack_version"]
        if (
            constants.OpenStackVersion["xena"]
            >= constants.OpenStackVersion[openstack_version]
        ):
            return "Cirros-5.1"
        return "Cirros-6.0"
