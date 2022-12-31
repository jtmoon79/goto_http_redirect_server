#!/usr/bin/env bash
#
# install and configure authbind
# usage:
#     authbind-install.sh [AUTHBIND USER [AUTHBIND PORT]]

set -e
set -u

HERED=$(dirname -- "${0}")
USERA=${1-nobody}
PORT=${2-80}

if ! which authbind &>/dev/null; then
    "${HERED}/pkg-install.sh" authbind
fi

set -x
touch "/etc/authbind/byport/${PORT}"
chown -v "${USERA}" "/etc/authbind/byport/${PORT}"
chmod -v 0500 "/etc/authbind/byport/${PORT}"
