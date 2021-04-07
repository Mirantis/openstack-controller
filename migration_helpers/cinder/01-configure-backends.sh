#!/bin/bash

set -e

RUN_DIR=$(cd $(dirname "$0") && pwd)
TOP_DIR=$( cd $(dirname $RUN_DIR/../../) && pwd)

. $TOP_DIR/globals
. $TOP_DIR/functions-common

function mcp2_import_cinder_backends_config {
    local backends_map=$(salt $(get_first_active_minion '-C I@cinder:volume') pillar.items cinder:volume:backend --out=json | jq '.[]|."cinder:volume:backend"')
    if [ "${backends_map}" == '{}' ]; then
        backends_map=$(salt $(get_first_active_minion '-C I@cinder:controller') pillar.items cinder:controller:backend --out=json | jq '.[]|."cinder:controller:backend"')
    fi
    local default_volume_type=$(salt $(get_first_active_minion '-C I@cinder:volume') pillar.get cinder:volume:default_volume_type --out=json | jq -r '.[]')
    if [ -z ${default_volume_type} ]; then
        default_volume_type=$(salt $(get_first_active_minion '-C I@cinder:controller') pillar.get cinder:controller:default_volume_type --out=json | jq -r '.[]')
    fi

    info "MCP1 backends map is:"
    info "${backends_map}"

    echo "${backends_map}" | jq -c --arg def_vol_type $default_volume_type \
                               '{"spec":
                                    {"services":
                                        {"block-storage":
                                            {"cinder":
                                                {"values":
                                                    {"conf":
                                                        {"backends":
                                                            (with_entries
                                                               (.value |=
                                                                  {volume_driver: "cinder.volume.drivers.rbd.RBDDriver",
                                                                   volume_backend_name: .backend,
                                                                   rbd_pool: .pool,
                                                                   rbd_user: .user,
                                                                   rbd_secret_uuid_fake: .secret_uuid,
                                                                   backend_host: (if .backend_host then .backend_host
                                                                                  elif .host then .host
                                                                                  else "" end)
                                                                  }
                                                                )
                                                              ),
                                                            "cinder":
                                                               {"DEFAULT":
                                                                   {"enabled_backends":(map(.backend) | join(",")),
                                                                    "default_volume_type": $def_vol_type,
                                                                    "volume_name_template": "volume-%s",
                                                                   }
                                                               }
                                                           }
                                                       }
                                                   }
                                               }
                                            }
                                        }
                                    }' > cinder_conf.json
    info "MCP2 resulting backends configuration:"
    info "$(cat cinder_conf.json | jq '.')"

    if [ "${1}" != '--dry-run' ]; then
        info "Applying MCP2 backends configuration. Openstack deployment object ${OPENSTACK_DEPLOYMENT_OBJECT_NAME} will be patched"
        kubectl -n openstack patch osdpl "${OPENSTACK_DEPLOYMENT_OBJECT_NAME}" -p $(cat cinder_conf.json) --type merge
    fi
}

mcp2_import_cinder_backends_config $@
