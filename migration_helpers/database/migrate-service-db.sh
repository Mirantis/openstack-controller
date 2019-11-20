#!/bin/bash

RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$( cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/database/functions

mkdir -p $DATABASE_DIR
for component in $COMPONENTS_TO_MIGRATE_DB; do
    check_database_connection $component $(get_mcp1_database_address) $(get_mcp1_database_username $component) $(get_mcp1_database_password $component)
    get_database_size $component $(get_mcp1_database_address) $(get_mcp1_database_username $component) $(get_mcp1_database_password $component)
    dump_openstack_component_dbs $component
    check_database_connection $component $(get_mcp2_database_address) $(get_mcp2_database_username $component) $(get_mcp2_database_password $component)
    drop_database_on_target $component
    import_openstack_component_dbs $component
done
