#!/usr/bin/env bash
source tools/get_service_account.sh
python3 tools/set-cluster-insecure.py $KUBECFG_FILE_NAME
export NODE_IP=${NODE_IP:$(ip route get 4.2.2.1 | awk '{print $7}' | head -1)}
docker-compose -f tools/docker-compose.yaml $@
