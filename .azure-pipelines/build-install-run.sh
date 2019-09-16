#!/usr/bin/env bash
# for Azure Pipelines task

set -e
set -u
set -o pipefail

# initial $PWD is at project root directory
BUILD_INSTALL='./tools/build-install.sh'

# dump much information about the Azure Pipelines environment
set -x
whoami
hostname
pwd
env | sort
ls -la .
uname -a
docker info || true
python --version
python -m pip --version
python -m pip list -vvv

python -m pip install --quiet --upgrade pip
python -m pip install --quiet --upgrade setuptools
python -m pip install --quiet --user twine

# run the build-install.sh
chmod +x "${BUILD_INSTALL}"  # force +x
"${BUILD_INSTALL}" --uninstall
