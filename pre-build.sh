#!/bin/bash

set -ex

GERRIT_SCHEME=${GERRIT_SCHEME:-$(git remote -v | sed -n -e 's|^origin[[:space:]]\+\([[:alpha:]]\+\)://\([a-z0-9\-]\+\)@\([a-z.:0-9]\+\)/.*(fetch)$|\1|p')}
GERRIT_NAME=${GERRIT_NAME:-$(git remote -v | sed -n -e 's|^origin[[:space:]]\+\([[:alpha:]]\+\)://\([a-z0-9\-]\+\)@\([a-z.:0-9]\+\)/.*(fetch)$|\2|p')}
GERRIT_HOST_PORT=${GERRIT_HOST_PORT:-$(git remote -v | sed -n -e 's|^origin[[:space:]]\+\([[:alpha:]]\+\)://\([a-z0-9\-]\+\)@\([a-z.:0-9]\+\)/.*(fetch)$|\3|p')}
MCP_K8S_LIB_REPO="${GERRIT_SCHEME}://${GERRIT_NAME}@${GERRIT_HOST_PORT}/mcp/mcp-k8s-lib.git"
OSH_OPERATOR_BASE_PATH=${OSH_OPERATOR_BASE_PATH:-/opt/operator}


WORKDIR=$(dirname $0)
DATA_DIR=${WORKDIR}/data
REQUIREMENTS_FILE=${WORKDIR}/requirements.txt
TEST_REQUIREMENTS_FILE=${WORKDIR}/test-requirements.txt

function prepare(){
    mkdir -p $DATA_DIR; pushd $DATA_DIR
    ls -lah
    if [ ! -d mcp-k8s-lib ] ; then
      git clone ${MCP_K8S_LIB_REPO}
      pushd mcp-k8s-lib; git checkout $MCP_K8S_LIB_TAG; popd
    fi
    popd
    # Use path that will be available in Dockerfile
    sed -i -e "s|^mcp-k8s-lib|file://${OSH_OPERATOR_BASE_PATH}/data/mcp-k8s-lib#egg=mcp-k8s-lib|g" ${REQUIREMENTS_FILE};
    # For unknown reason mcp-k8s-lib dependencies are not installed, copy them explicitly
    # TODO figure out why it happening
    while IFS= read -r line; do
        requirement=$(echo "$line"| sed -n -e 's|^\([[:alpha:]]\+\).*|\1|p')
        if ! grep -qw $requirement ${REQUIREMENTS_FILE}; then
            echo "$requirement" >> $REQUIREMENTS_FILE
        else
            echo "$requirement is present in dependencies"
        fi
    done < "${DATA_DIR}/mcp-k8s-lib/requirements.txt"
}

case "$1" in
  *) echo "Attempt to prepare.."
    prepare
    ;;
esac
