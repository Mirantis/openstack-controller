#!/bin/sh

# install pre-cloned dependencies that are not available in PyPI

set -ex

WORKDIR=$(dirname $0)
DATA_DIR=${WORKDIR}/data

build_cmd="pip wheel"
build_args=""
for d in `ls $DATA_DIR`; do
    build_args="$build_args $DATA_DIR/$d"
done

$build_cmd $build_args $@

exit $?
