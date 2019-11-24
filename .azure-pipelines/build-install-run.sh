#!/usr/bin/env bash
#
# for Azure Pipelines job where
#     vmImage: 'ubuntu-16.04'
# or
#     vmImage: 'macOS-10.14'
#
# XXX: nearly identical to .circleci/build-install-run.sh
# XXX: very similar to tools/build-install.sh

set -e
set -u
set -o pipefail

# initial $PWD is at project root directory
readonly PACKAGE_NAME='goto_http_redirect_server'
readonly PROGRAM_NAME='goto_http_redirect_server'

# dump much information about the Azure Pipelines environment
set -x
whoami
hostname
pwd
cat /etc/os-release || true
env | sort
ls -la .
uname -a
docker info || true
python --version
python -m pip --version
python -m pip list -vvv

# install and upgrade necessary packages
python -m pip install --quiet --upgrade pip
python -m pip install --quiet --upgrade setuptools
python -m pip install --quiet --user twine
python -m pip install --quiet --user mypy
python -m pip --version
python -m twine --version
python -m mypy --version

function readlink_(){
    # portable readlink
    echo -n "${1}" | python -B -c '\
import os, sys
input_ = sys.stdin.read()
print(os.path.realpath(input_))'
}

# condensed from tools/build-install.sh
# update path with potential pip install locations
usersite=$(python -B -c 'import site; print(site.USER_SITE);')
userbase=$(python -B -c 'import site; print(site.USER_BASE);')
userbasebin=${userbase}/bin  # --user install location on Ubuntu
export PATH="${PATH}:${usersite}:${userbase}:${userbasebin}"

SERVER_TEST=$(readlink_ "./tools/ci/server-test.sh")
python -m mypy 'goto_http_redirect_server/goto_http_redirect_server.py'
# build
version=$(python -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)')
python setup.py -v bdist_wheel
cv_whl=$(readlink_ "./dist/${PACKAGE_NAME}-${version}-py3-none-any.whl")
python -m twine check "${cv_whl}"
cd ..  # move out of project directory so pip install behaves correctly
# install
python -m pip install --user --verbose "${cv_whl}"
# run
"${PROGRAM_NAME}" --version
# server test
chmod -v +x "${SERVER_TEST}"
"${SERVER_TEST}"
# uninstall
python -m pip uninstall --yes --verbose "${PACKAGE_NAME}"
