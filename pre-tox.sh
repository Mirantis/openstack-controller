#!/bin/bash

# For case when running on CI and tox
export OSH_OPERATOR_BASE_PATH=${WORKSPACE}
WORKDIR=$(dirname $0)

${WORKDIR}/pre-build.sh
