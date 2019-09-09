#!/usr/bin/env bash
#
# uninstall, build, install, run
#

set -e
set -u
set -o pipefail

# if $PTYHON is set, assume it's the PYTHON interpreter
if [ ! "${PYTHON+x}" ]; then
    # attempt to set python to most portable invocation
    PYTHON='python'  # fallback
    if which 'python3' &> /dev/null; then
        PYTHON='python3'  # Linux Python 3
    elif which 'py' &> /dev/null; then
        PYTHON='py -3'  # Windows launcher
    fi
fi
${PYTHON} --version  # sanity check it runs

cd "$(dirname -- "${0}")"  # cd to project top-level

readonly PACKAGE_NAME='goto_http_redirect_server'
readonly PROGRAM_NAME='goto_http_redirect_server'

# Debian bash on Windows Linux Subsystem may not have default pip install path
if [ -d ~/.local/bin ]; then
    export PATH=${PATH}:~/.local/bin
fi

set -x
# uninstall any previous install (must be done outside the project directory)
cd ..

${PYTHON} -m pip uninstall --yes --verbose "${PACKAGE_NAME}" || true

# remove previous build artifacts
rm -rfv ./build/ ./dist/ "./${PACKAGE_NAME}.egg-info/"

# build using wheels
cd -
version=$(${PYTHON} -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)')
userbase=$(${PYTHON} -B -c 'import site; site.getuserbase(); print(site.USER_BASE)')  # pip will install to here
export PATH="${PATH}:${userbase}"

${PYTHON} setup.py -v bdist_wheel

# note the contents of dist
ls -l ./dist/

set +x
# get the full path to the wheel file
# (usually, `basename $PWD` is 'goto_http_redirect_server' but on circleci it's 'project')
cv_whl=$(readlink -f -- "./dist/${PACKAGE_NAME}-${version}-py3-none-any.whl")
if ! [[ -f "${cv_whl}" ]]; then
    cv_whl=$(readlink -f -- "./dist/${PACKAGE_NAME}-${version}-py3.7-none-any.whl")
fi

# install the wheel (must be done outside the project directory)
(   
    cd ..
    set -x
    ${PYTHON} -m pip install --user --verbose "${cv_whl}"
)

# make sure to attempt uninstall if asked
uninstall=false
if [[ "${1+x}" == '--uninstall' ]]; then
    uninstall=true
fi
function on_exit(){
    if ${uninstall}; then
      set -x
      ${PYTHON} -m pip uninstall --yes --verbose "${PACKAGE_NAME}"
    fi
}
trap on_exit EXIT

PORT=55923  # hopefully not used
(
    set -x
    # does it run?
    "${PACKAGE_NAME}" --version
    # does it run and listen on the socket?
    "${PACKAGE_NAME}" --verbose --shutdown 2 --port ${PORT} --from-to '/a' 'http://foo.com'
)

if ${uninstall}; then
    # and test uninstall if asked
    (
        set -x
        ${PYTHON} -m pip uninstall --yes --verbose "${PACKAGE_NAME}"
    )
    # if script got here then no need to run uninstall on EXIT
    uninstall=false
else
    echo "
To uninstall remaining package:

        ${PYTHON} -m pip uninstall --yes --verbose '${PACKAGE_NAME}'

or run this script with '--uninstall'
"
fi

echo 'Success!'
