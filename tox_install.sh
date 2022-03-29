#!/bin/bash

set -ex

WORKDIR=$(dirname $0)
install_cmd="pip install"

echo "$(date)" >> /tmp/env

$install_cmd $@

# Apply kopf patches
pushd $VIRTUAL_ENV/lib/python3.$(python3 -c 'import sys; print(sys.version_info.minor)')/site-packages
if [[ -d kopf && ! -f kopf/patches_applied ]]; then
  for p in $(ls $WORKDIR/kopf-patches/*.patch); do
    patch -p1 --forward < $p
  done
  touch kopf/patches_applied
fi
popd

exit $?
