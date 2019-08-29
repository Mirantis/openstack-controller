#!/bin/bash

set -ex

GERRIT_SCHEME=${GERRIT_SCHEME:-$(git remote -v | sed -n -e 's|^origin[[:space:]]\+\([[:alpha:]]\+\)://\([a-z0-9\-]\+\)@\([a-z.:0-9]\+\)/.*(fetch)$|\1|p')}
GERRIT_NAME=${GERRIT_NAME:-$(git remote -v | sed -n -e 's|^origin[[:space:]]\+\([[:alpha:]]\+\)://\([a-z0-9\-]\+\)@\([a-z.:0-9]\+\)/.*(fetch)$|\2|p')}
GERRIT_HOST_PORT=${GERRIT_HOST_PORT:-$(git remote -v | sed -n -e 's|^origin[[:space:]]\+\([[:alpha:]]\+\)://\([a-z0-9\-]\+\)@\([a-z.:0-9]\+\)/.*(fetch)$|\3|p')}
MCP_K8S_LIB_REPO="${GERRIT_SCHEME}://${GERRIT_NAME}@${GERRIT_HOST_PORT}/mcp/mcp-k8s-lib.git"
MCP_K8S_LIB_TAG=${MCP_K8S_LIB_TAG:-master}

WORKDIR=$(dirname $0)
DATA_DIR=${WORKDIR}/data

echo "Attempt to prepare.."
mkdir -p $DATA_DIR; pushd $DATA_DIR
ls -lah
if [[ ! -d mcp-k8s-lib ]] ; then
  git clone ${MCP_K8S_LIB_REPO}
fi
pushd mcp-k8s-lib
git checkout $MCP_K8S_LIB_TAG
popd
popd
