#!/bin/bash -e
#
# THIS FILE IS GOING TO BE EXECUTED ON ANY CFG NODES (MCP1).
#
RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$(cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common

echo "
values:
  endpoints:
    identity:
      auth:
        heat_stack_user:
          domain_name: $(salt-call pillar.get _param:mcp1_heat_domain_name --out json | jq -r '.[]')
          username: $(salt-call pillar.get _param:mcp1_heat_username --out json | jq -r '.[]')
          password: $(salt-call pillar.get _param:mcp1_heat_username_password --out json | jq -r '.[]')
"
