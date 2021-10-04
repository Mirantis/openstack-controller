#!/bin/bash

set -ex

WORKDIR=$(dirname $0)
install_cmd="pip install"

echo "$(date)" >> /tmp/env

$install_cmd $@

# Apply kopf patches
pushd $VIRTUAL_ENV/lib/python3.$(python3 -c 'import sys; print(sys.version_info.minor)')/site-packages
if [[ -d kopf && ! -f kopf/kopf-session-timeout.patch_applied ]]; then
patch -p1 --forward < $WORKDIR/kopf-session-timeout.patch
touch kopf/kopf-session-timeout.patch_applied
fi
popd

exit $?
