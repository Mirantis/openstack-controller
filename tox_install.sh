#!/bin/bash

set -ex

WORKDIR=$(dirname $0)
# this is for local test runs only,
# as pre-build.sh is called in CI before tox
DATA_DIR=${WORKDIR}/data
if [[ ! -d ${DATA_DIR} ]]; then
    ${WORKDIR}/pre-build.sh
fi
${WORKDIR}/install.sh $@
