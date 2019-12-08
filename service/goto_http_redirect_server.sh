#!/usr/bin/env bash
#
# systemd wrapper for goto_http_redirect_server
# accepts some command-line options for adjusting process ownership and access-levels
# various parameters may be overridden by environment variables
#
# XXX: makes presumptions! needs work to be more portable!
# XXX: only tested on Debian 9

set -u
set -e
set -o pipefail

authbind=
sudoas=
nice=
port=
debug=

while getopts "au:n:p:dh?" opt; do
    case ${opt} in
        a)
            authbind='authbind --deep'
            ;;
        u)
            sudoas="sudo -u ${OPTARG} --"
            ;;
        n)
            nice="nice -n ${OPTARG}"
            ;;
        p)
            port="--port ${OPTARG}"
            ;;
        d)
            debug='--debug'
            ;;
        h)
            ;&
        \?)
            (
                echo "Usage: ${0} [-a] [-u USER] [-n NICE] [-p PORT] [-d]"
                echo
                echo "       -a  lower privilege using 'authbind --deep' (requires authbind)"
                echo "       -u  run process using 'sudo -u USER'  (requires sudo)"
                echo "       -n  run process with nice level NICE"
                echo "       -p  pass '--port PORT' option"
                echo "       -d  pass '--debug' option"
                echo
                echo "Usage: ${0} [-h] [-?]"
                echo
                echo "       This help message"
            ) >&2
            exit 4
            ;;
    esac
done

GOTO_IP_ADDR=${GOTO_IP_ADDR:-'0.0.0.0'}
GOTO_LOG=${GOTO_LOG-/var/log/goto_http_redirect_server.log}
GOTO_SCRIPT=${GOTO_SCRIPT:-/usr/local/bin/goto_http_redirect_server}
GOTO_REDIRECTS_FILE=${GOTO_REDIRECTS_FILE:-/usr/local/share/goto_http_redirect_server.csv}
GOTO_PATH_STATUS=${GOTO_PATH_STATUS-/}
GOTO_PATH_RELOAD=${GOTO_PATH_RELOAD-/reload}

declare -a GOTO_PATH_STATUS_PARAMS=()
if [[ "${GOTO_PATH_STATUS}" ]]; then
     GOTO_PATH_STATUS_PARAMS[0]='--status-path'
     GOTO_PATH_STATUS_PARAMS[1]=${GOTO_PATH_STATUS}
fi
declare -a GOTO_PATH_RELOAD_PARAMS=()
if [[ "${GOTO_PATH_RELOAD}" ]]; then
     GOTO_PATH_RELOAD_PARAMS[0]='--reload-path'
     GOTO_PATH_RELOAD_PARAMS[1]=${GOTO_PATH_RELOAD}
fi

set -x
exec \
    ${sudoas} \
        ${authbind} \
            ${nice} \
                ${GOTO_SCRIPT} \
                    --redirects "${GOTO_REDIRECTS_FILE}" \
                    --ip "${GOTO_IP_ADDR}" \
                    ${port} \
                    "${GOTO_PATH_STATUS_PARAMS[@]}" \
                    "${GOTO_PATH_RELOAD_PARAMS[@]}" \
                    --log "${GOTO_LOG}" \
                    ${debug}
