#!/usr/bin/env bash
# for Azure Pipelines task

set -e
set -u
set -o pipefail

# initial $PWD is at project root directory
readonly BUILD_INSTALL='./tools/build-install.sh'
readonly PACKAGE_NAME='goto_http_redirect_server'
readonly PROGRAM_NAME='goto_http_redirect_server'

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

# install and upgrade necessary packages
python -m pip install --quiet --upgrade pip
python -m pip install --quiet --upgrade setuptools
python -m pip install --quiet --user twine
python -m pip --version
python -m twine --version

# condensed from tools/build-install.sh
# update path with potential pip install locations
usersite=$(python -B -c 'import site; print(site.USER_SITE);')
userbase=$(python -B -c 'import site; print(site.USER_BASE);')
userbasebin=${userbase}/bin  # --user install location on Ubuntu
export PATH="${PATH}:${usersite}:${userbase}:${userbasebin}"
# build
version=$(python -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)')
python setup.py -v bdist_wheel
cv_whl=$(readlink -f -- "./dist/${PACKAGE_NAME}-${version}-py3-none-any.whl")
python -m twine check "${cv_whl}"
cd ..  # move out of project directory
# install
python -m pip install --user --verbose "${cv_whl}"
# run
PORT=55923  # hopefully not in-use!
"${PROGRAM_NAME}" --version
# does it run and listen on the socket?
"${PROGRAM_NAME}" --debug --shutdown 2 --port ${PORT} --from-to '/a' 'http://foo.com'
# uninstall
python -m pip uninstall --yes --verbose "${PACKAGE_NAME}"
