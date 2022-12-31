#!/usr/bin/env bash
#
# copy and chmod the systemd service files
# optionally, enable the service
#
# assumes goto_http_redirect_server has been installed and is in the $PATH
 

set -e
set -u
set -o pipefail

GOTO_FILE_REDIRECTS=/usr/local/share/goto_http_redirect_server.csv
GOTO_FILE_SCRIPT=/usr/local/bin/goto_http_redirect_server
GOTO_SYSTEMD_SH=/usr/local/bin/goto_http_redirect_server.sh
GOTO_CONFIG=/etc/goto_http_redirect_server.conf
GOTO_SERVICE=goto_http_redirect_server.service
GOTO_FILE_SERVICE=/etc/systemd/user/${GOTO_SERVICE}

enable=false
start=false

if ! which getopt &>/dev/null; then
    echo "ERROR: GNU getopt not found. It is part of util-linux package." >&2
    exit 1
fi

options=$(getopt -n "$(basename -- "${0}")" -o "esh?" -l "enable,start,help" -- "${@}")
eval set -- "${options}"

while true; do
    case "${1-}" in
        -e|--enable)
            enable=true
            shift
            ;;
        -s|--start)
            start=true
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            ;&
        h|help)
            ;&
        \?)
            (
                echo "Usage: ${0} [-e|--enable] [-s|--start]"
                echo
                echo "       -e  enable systemd service"
                echo "       -s  start systemd service (requires -e)"
                echo
                echo "Usage: ${0} [-h|--help|-?]"
                echo
                echo "       This help message"
            ) >&2
            exit 4
            ;;
    esac
done

if ${start} && ! ${enable}; then
    echo "Warning: --start without --enable will probably fail" >&2
fi

cd "$(dirname -- "${0}")/.."

# create redirects file
touch "${GOTO_FILE_REDIRECTS}"
chmod -v 0644 -- "${GOTO_FILE_REDIRECTS}"

# cp or link goto_http_redirect_server
if which goto_http_redirect_server &>/dev/null; then
    ln -fvs -- "$(which goto_http_redirect_server)" "${GOTO_FILE_SCRIPT}"
else
    cp -v -- ./goto_http_redirect_server/goto_http_redirect_server.py "${GOTO_FILE_SCRIPT}"
fi

# copy systemd wrapper
cp -v -- ./service/goto_http_redirect_server.sh "$(dirname -- "${GOTO_SYSTEMD_SH}")"
chmod -v 0755 -- "${GOTO_SYSTEMD_SH}"

# copy systemd wrapper configuration
cp -v -- ./service/goto_http_redirect_server.conf "${GOTO_CONFIG}"
chmod -v 0600 -- "${GOTO_CONFIG}"

# copy systemd service
cp -v -- ./service/goto_http_redirect_server.service "$(dirname -- "${GOTO_FILE_SERVICE}")"
chmod -v 0444 -- "${GOTO_FILE_SERVICE}"

# note settings of important files
ls -l \
    "${GOTO_FILE_REDIRECTS}" \
    "${GOTO_FILE_SCRIPT}" \
    "${GOTO_SYSTEMD_SH}" \
    "${GOTO_CONFIG}" \
    "${GOTO_FILE_SERVICE}"

if ${enable}; then
    (
        set -x
        systemctl enable "${GOTO_FILE_SERVICE}"
    )
fi

if ${start}; then
    (
        set -x
        systemctl start "${GOTO_SERVICE}"
    )
fi
