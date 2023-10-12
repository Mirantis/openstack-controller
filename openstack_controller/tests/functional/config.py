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
        self.TEST_FLAVOR_SMALL_NAME = "m1.small"
        self.TEST_FLAVOR_NAME = "m1.extra_tiny_test"
        self.TEST_SUBNET_RANGE = "10.20.30.0/24"
        self.TEST_IPV6_SUBNET_RANGE = "2001:db8::/48"
        self.TEST_LB_SUBNET_RANGE = "192.168.0.0/24"
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

        # Time in seconds to wait for a volume create. Default is 30 seconds. Small volume is cirros based (up to 100Mb)
        self.VOLUME_SMALL_CREATE_TIMEOUT = 30
        # Time in seconds to wait for a volume create. Default is 30 seconds. Medium volume is Ubuntu based (up to 1Gb)
        self.VOLUME_MEDIUM_CREATE_TIMEOUT = 300
        # Interval in seconds to check the volume status. Default is 1 second.
        self.VOLUME_READY_INTERVAL = 1
        # Size, in GB of the volume to create.
        self.VOLUME_SIZE = 1
        # Time in seconds to wait for a cinder pool timestamp updated. Default is 60 seconds
        self.CINDER_POOL_UPDATE_TIMEOUT = 60
        # Interval in seconds to check the cinder pool timestamp. Default is 3 second.
        self.CINDER_POOL_UPDATE_INTERVAL = 3

        # The Neutron PortProber exporter port
        self.PORTPROBER_EXPORTER_PORT = 8000

        # Time in seconds to wait for metric update. Is the period how often probber sends metrics.
        # prometheus scrape inteval 20 + 2 x cloudprober probe interval 15 + file surfacer update timeout 10
        self.PORTPROBER_PROBE_INTERVAL = 60

        # Time in seconds to wait for metric to appear. The cloudprober refreshes targets priodically,
        # so wait while metrics appear in cloudprober.
        # PORTPROBER_PROBE_INTERVAL + cloudprober file check interval 30
        self.PORTPROBER_METRIC_REFRESH_TIMEOUT = (
            self.PORTPROBER_PROBE_INTERVAL + 30
        )

        # Number of portprober agents to host nework
        self.PORTPROBER_AGENTS_PER_NETWORK = 2

        # Interval in seconds to wait for a loadbalancer operation. Default is 10 second.
        self.LB_OPERATION_INTERVAL = 10
        # Time in seconds to wait for a loadbalancer action is completed. Default is 300 second.
        self.LB_OPERATION_TIMEOUT = 300

    def get_cirros_image(self):
        openstack_version = self._osdpl.obj["spec"]["openstack_version"]
        if (
            constants.OpenStackVersion["xena"]
            >= constants.OpenStackVersion[openstack_version]
        ):
            return "Cirros-5.1"
        return "Cirros-6.0"
