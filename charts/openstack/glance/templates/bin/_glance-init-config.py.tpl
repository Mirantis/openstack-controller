#!/usr/bin/env python3

import os

CONF_PATH="/etc/glance/glance-api.conf.d/"
EXTRA_CONF="01-glance.conf"

pod_ip = os.getenv("POD_IP", "envvars")
glance_internal_port = os.getenv("GLANCE_API_SERVICE_PORT", "envvars")
with open(CONF_PATH + EXTRA_CONF, 'w') as f:
    f.write(f"[DEFAULT]\nworker_self_reference_url = http://{pod_ip}:{glance_internal_port}\n")
