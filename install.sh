#!/bin/sh

# install pre-cloned dependencies that are not available in PyPI

set -ex

WORKDIR=$(dirname $0)
DATA_DIR=${WORKDIR}/data

install_cmd="pip install"
install_args=""
for d in `ls $DATA_DIR`; do
    install_args="$install_args $DATA_DIR/$d"
done

$install_cmd $install_args $@

exit $?
