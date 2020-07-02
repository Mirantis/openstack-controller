#!/bin/bash

set -ex

WORKDIR=$(dirname $0)
install_cmd="pip install"

echo "$(date)" >> /tmp/env

$install_cmd $@

# Apply kopf patches
pushd $VIRTUAL_ENV/lib/python3.7/site-packages
patch -p1 --forward < $WORKDIR/kopf-session-timeout.path || true
popd

exit $?
