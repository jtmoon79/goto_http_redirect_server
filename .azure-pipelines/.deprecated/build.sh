#!/usr/bin/env bash
#
# for Azure Pipelines job where
#     vmImage: 'ubuntu-16.04'
# or
#     vmImage: 'macOS-10.14'
#
# assumes $PWD is project root

set -e
set -u
set -o pipefail

readonly PACKAGE_NAME='goto_http_redirect_server'
BUILD_ARTIFACTSTAGINGDIRECTORY=${BUILD_ARTIFACTSTAGINGDIRECTORY-/tmp}  # should be defined in Azure Pipeline

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

# install and upgrade necessary packages
python --version
python -m pip --version
python -m pip list -vvv
python -m pip install --quiet --upgrade pip setuptools
python -m pip install --quiet --user twine mypy
python -m pip --version
python -m twine --version
python -m pip list -vvv

# portable readlink
function readlink_(){
    echo -n "${1}" | python -B -c '\
import os, sys
input_ = sys.stdin.read()
print(os.path.realpath(input_))'
}

# build
version=$(python -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)')
python setup.py -v bdist_wheel
cv_whl=$(readlink_ "./dist/${PACKAGE_NAME}-${version}-py3-none-any.whl")
python -m twine check "${cv_whl}"

ls -la ./dist/  # REMOVE THIS

# copy to artifact staging directory
#cp -av -- "${cv_whl}" "${BUILD_ARTIFACTSTAGINGDIRECTORY}"
