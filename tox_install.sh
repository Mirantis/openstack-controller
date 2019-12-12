#!/bin/bash

set -ex

WORKDIR=$(dirname $0)
# this is for local test runs only,
# as pre-build.sh is called in CI before tox
DATA_DIR=${WORKDIR}/data
if [[ ! -d ${DATA_DIR} ]]; then
    ${WORKDIR}/pre-build.sh
fi
# install pre-cloned dependencies that are not available in PyPI
install_cmd="pip install"
install_args=""
for d in `ls $DATA_DIR`; do
    install_args="$install_args $DATA_DIR/$d"
done

$install_cmd $install_args $@

exit $?
