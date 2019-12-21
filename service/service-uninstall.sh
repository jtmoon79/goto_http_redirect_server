#!/usr/bin/env bash
#
# remove systemd service files
# optionally, --reload systemd
# optionally, --wipe goto_http_redirect_server configuration files
#
 

set -e
set -u
set -o pipefail

GOTO_FILE_REDIRECTS=/usr/local/share/goto_http_redirect_server.csv
GOTO_SYSTEMD_SH=/usr/local/bin/goto_http_redirect_server.sh
GOTO_CONFIG=/etc/goto_http_redirect_server.conf
GOTO_SERVICE=goto_http_redirect_server.service
GOTO_FILE_SERVICE=/etc/systemd/user/${GOTO_SERVICE}

reload=false
wipe=false

if ! which getopt &>/dev/null; then
    echo "ERROR: GNU getopt not found. It is part of util-linux package." >&2
    exit 1
fi

options=$(getopt -n "$(basename -- "${0}")" -o "rwh?" -l "reload,wipe,help" -- "${@}")
eval set -- "${options}"

while true; do
    case "${1-}" in
        -r|--reload)
            reload=true
            shift
            ;;
        -w|--wipe)
            wipe=true
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
                echo "Usage: ${0} [-r|--reload] [-w|--wipe]"
                echo
                echo "       -r  reload systemd"
                echo "       -w  wipe (remove) configuration files:"
                echo "           ${GOTO_CONFIG}"
                echo "           ${GOTO_FILE_REDIRECTS}"
                echo
                echo "Usage: ${0} [-h|--help|-?]"
                echo
                echo "       This help message"
            ) >&2
            exit 4
            ;;
    esac
done

cd "$(dirname -- "${0}")/.."

set +e            # no `set -e`; attempt to remove as much as possible
declare -i ret=0  # but signal remove failures in script return code

rm -v -- "${GOTO_SYSTEMD_SH}" "${GOTO_FILE_SERVICE}" || ret=1

if ${reload}; then
    (
        set -x
        systemctl stop "${GOTO_SERVICE}"
        systemctl disable "${GOTO_SERVICE}"
    )
    rm -v -- "${GOTO_SYSTEMD_SH}" "${GOTO_FILE_SERVICE}" || ret=1
    (
        set -x
        systemctl daemon-reload
        systemctl reset-failed
    )
    shift
fi

if ${wipe}; then
    rm -v -- "${GOTO_CONFIG}" "${GOTO_FILE_REDIRECTS}" || ret=1
    shift
fi

exit ${ret}
