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
docker info || true
python --version
pip --version
pip list -vvv

# install ahead of time
python -m pip install --quiet --user --upgrade pip
python -m pip install --quiet --user --upgrade setuptools
python -m pip install --quiet --user twine
python -m pip install --quiet --user mypy

# run the build-install.sh
chmod +x "${BUILD_INSTALL}"  # force +x
"${BUILD_INSTALL}" --uninstall
