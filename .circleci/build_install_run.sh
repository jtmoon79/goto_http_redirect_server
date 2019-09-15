#!/usr/bin/env bash
# for CircleCI job build_install_run

set -e
set -u
set -o pipefail

BUILD_INSTALL="$(dirname -- "${0}")/../tools/build-install.sh"

# dump much information about the CircleCI environment
set -x
whoami
pwd
env | sort
ls -la .
uname -a
docker info
python --version
pip --version

# install ahead of time
pip install --user twine

# run the build-install.sh
chmod +x "${BUILD_INSTALL}"  # force +x
"${BUILD_INSTALL}" --uninstall
