#!/usr/bin/env bash
#
# for CircleCI job build_install_run
#
# TODO: break this up into jobs for Circle CI Pipeline
# $PWD is presumed to be at project root directory

set -e
set -u
set -o pipefail

readonly PACKAGE_NAME='goto_http_redirect_server'
readonly PROGRAM_NAME='goto_http_redirect_server'
readonly REALPATH=./tools/realpath.sh
readonly MYPY=./tools/mypy.sh

# dump much information about the CircleCI environment
set -x
whoami
pwd
env | sort
cat /etc/os-release || true
ls -la .
uname -a
docker info || true
python --version
pip --version
pip list -vvv

# setup scripts
# BUG: set git file mode instead
chmod -v +x -- "${REALPATH}" "${MYPY}"
SERVER_TEST=$("${REALPATH}" './tools/ci/server-test.sh')
PY_TEST=$("${REALPATH}" './tools/pytest.sh')
chmod -v +x -- "${SERVER_TEST}" "${PY_TEST}"

# XXX: installation of packages will install cffi which runs make rule `build_rust`
#      rust compiler is not available on CircleCI Alpine image so forcefully skip it
export CRYPTOGRAPHY_DONT_BUILD_RUST=1
# install and upgrade necessary packages
python -m pip install --quiet --user --upgrade pip setuptools
python -m pip install --quiet --user twine mypy
python -m pip list --disable-pip-version-check --no-index -vvv

source ./tools/ci/PATH-add-pip-site.sh

# install development requirements
python -m pip install --user --verbose -e '.[development]'

# mypy test
"${MYPY}"

# build
version=$(python -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)')
python setup.py -v bdist_wheel
cv_whl=$("${REALPATH}" "./dist/${PACKAGE_NAME}-${version}-py3-none-any.whl")
python -m twine check "${cv_whl}"

cd ..  # move out of project directory so pip install behaves correctly

# install
python -m pip install --user --verbose "${cv_whl}"

# run
"${PROGRAM_NAME}" --version

# pytest test
"${PY_TEST}"

# server test
"${SERVER_TEST}"

# uninstall
python -m pip uninstall --yes --verbose "${PACKAGE_NAME}"
