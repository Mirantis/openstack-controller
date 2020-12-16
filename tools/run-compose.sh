#!/usr/bin/env bash
source tools/get_service_account.sh
python3 tools/set-cluster-insecure.py $KUBECFG_FILE_NAME
docker-compose -f tools/docker-compose.yaml $@
