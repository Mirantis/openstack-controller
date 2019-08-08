#!/bin/bash

# Many of neutron's repos suffer from the problem of depending on neutron,
# but it not existing on pypi. This ensures its installed into the test environment.
set -ex

WORKDIR=$(dirname $0)

install_cmd="pip install"

${WORKDIR}/pre-build.sh

if [ -z "$@" ]; then
  echo "No packages to be installed."
  exit 0
fi

$install_cmd  $*

exit $?
