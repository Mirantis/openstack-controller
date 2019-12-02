#!/bin/bash -e
#
# THIS FILE IS GOING TO BE EXECUTED ON ANY CFG NODES (MCP1).
#
RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$(cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common

function get_key_archive_path {
  local key_dir=$1
  local key_directory=$(basename ${key_dir})
  local repository_path=$(dirname ${key_dir})
  echo "${key_directory}.tar.gz"
}

function pack_keystone_keys {
    local salt_out

    info "Packing keystone repository ${KEY_REPOSITORY}"
    for key_dir in ${KEY_REPOSITORY}; do
        info "Packing keystone key repository ${key_dir}"
        key_directory=$(basename ${key_dir})
        repository_path=$(dirname ${key_dir})
        key_arc_name="${key_directory}.tar.gz"
        salt_out=$(salt 'ctl01*' archive.tar czf $(get_key_archive_path $key_dir) ./${key_directory} cwd=\"${repository_path}\") || die $LINENO "Failed to pack keystone key $key_dir"
        info "Keystone keys were packed"
    done
}

function migrate_keystone_keys {
    local keys_pkg=$1
    local minion_ID
    local local_keys_pkg
    local local_pkg_name
    local keys_pkg_dirname
    local key_type=$(basename ${keys_pkg} .tar.gz)

    info "Migrating keystone key: $keys_pkg"
    local_pkg_name=$(basename ${keys_pkg})
    minion_ID=$(salt 'ctl01*' cp.push ${keys_pkg} upload_path=\"/${local_pkg_name}\" remove_source=True --out=json | jq 'keys[]' | tr -d '"')
    local_keys_pkg="/var/cache/salt/master/minions/${minion_ID}/files/${local_pkg_name}"

    keys_pkg_dirname=$(mktemp -d)
    tar -xzf ${local_keys_pkg} -C ${keys_pkg_dirname}/ || die $LINENO "Failed to extract archive with keys: $local_keys_pkg"
    kubectl delete secret keystone-${key_type} -n openstack || die $LINENO "Failed to delete secret with keys: keystone-${key_type}"
    kubectl create secret generic keystone-${key_type} --from-file=${keys_pkg_dirname}/${key_type} -n openstack || die $LINENO "Failed to update keys: keystone-${key_type}"
    rm -rf $keys_pkg_dirname
    info "Keys were updated: $keys_pkg"
}

function restart_keystone_api {
    info "Restarting keystone-api on MCP2"
    kubectl delete pods -l application=keystone,component=api -n openstack || die $LINENO "Failed to restart keystone api"
    info "Keystone API was restarted"
}

pack_keystone_keys
for key_dir in ${KEY_REPOSITORY}; do
    migrate_keystone_keys $(get_key_archive_path $key_dir)
done

restart_keystone_api
