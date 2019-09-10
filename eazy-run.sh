#!/usr/bin/env bash
#
# a lazy way to download and run goto_Http_redirect_server

set -e
set -u

URL='https://raw.githubusercontent.com/jtmoon79/goto_http_redirect_server/master/goto_http_redirect_server/goto_http_redirect_server.py'
NAME='goto_http_redirect_server.py'
SCRIPT="./${NAME}"

function exists() {
    which "${1}" &>/dev/null
}

if ! [ -f "${NAME}" ]; then
    if exists wget; then
        wget --quiet -O "${SCRIPT}" "${URL}"
    elif exists curl; then
        curl --silent --output "${SCRIPT}" --url "${URL}"
    else
        echo "ERROR: cannot find downloaders wget or curl" >&2
        exit 1
    fi
fi

chmod +x "${SCRIPT}"

# make an effort to find python3
PYTHON='python'
if exists 'python3.7'; then
    PYTHON='python3.7'
elif exists 'python3'; then
    PYTHON='python3'
elif exists 'py'; then
    PYTHON="py -3"
fi

function exit_(){
    echo >&2
    rm -v "${SCRIPT}"
}

trap exit_ EXIT

(
    set -x
    ${PYTHON} -B "${SCRIPT}" "${@}"
)

