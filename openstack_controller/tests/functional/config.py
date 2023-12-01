CIRROS_TEST_IMAGE_NAME = "Cirros-6.0"
TEST_FLAVOR_NAME = "m1.extra_tiny_test"
TEST_SUBNET_RANGE = "10.20.30.0/24"
PUBLIC_NETWORK_NAME = "public"

# Time in seconds to wait for a compute operation to complete. Default is 120 seconds.
COMPUTE_TIMEOUT = 60 * 2
# Interval in seconds to check the status of a compute resource. Default is 1 second.
COMPUTE_BUILD_INTERVAL = 1

# Time in seconds to wait for a metric value. Default is 30 seconds.
METRIC_TIMEOUT = 45
# Interval in seconds to check the metric value. Default is 1 second.
METRIC_INTERVAL_TIMEOUT = 5

# Time in seconds to wait for a volume operation to complete. Default is 60 seconds.
VOLUME_TIMEOUT = 30 * 2
# Interval in seconds to check the status of a compute resource. Default is 1 second.
VOLUME_BUILD_INTERVAL = 1

# Time in seconds to wait for a server to change a status. Default is 30 seconds.
SERVER_TIMEOUT = 30
# Interval in seconds to check the server status. Default is 1 second.
SERVER_READY_INTERVAL = 1
