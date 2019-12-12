#!/usr/bin/env bash
#
# systemd wrapper for goto_http_redirect_server.service
#
# Options may be adjusted via command-line or configuration file.
# Configuration file is defaults to /etc/goto_http_redirect_server.conf.
#

set -u
set -e
set -x

# if available, load configuration file
GOTO_CONF=${GOTO_CONF-/etc/goto_http_redirect_server.conf}
if [ -f "${GOTO_CONF}" ]; then
    source "${GOTO_CONF}"
fi

authbind=
if ${GOTO_AUTHBIND_ENABLE-false} &>/dev/null; then
    authbind='authbind --deep'
fi
sudoas=
if ${GOTO_SUDOAS_ENABLE-false} &>/dev/null; then
    sudoas="sudo -u ${GOTO_SUDOAS_USER} --"
fi
nice=
if ${GOTO_NICE_ENABLE-false} &>/dev/null; then
    nice="nice -n ${GOTO_NICE_LEVEL}"
fi
port=
if [ "${GOTO_PORT+x}" ]; then
    port="--port ${GOTO_PORT}"
fi
debug=
if ${GOTO_DEBUG_ENABLE-false} &>/dev/null; then
    debug='--debug'
fi

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
                echo "This script imports other settings from /etc/goto_http_redirect_server.conf"
                echo
                echo "Usage: ${0} [-h] [-?]"
                echo
                echo "       This help message"
            ) >&2
            exit 4
            ;;
    esac
done

GOTO_LISTEN_IP=${GOTO_LISTEN_IP:-'0.0.0.0'}
GOTO_FILE_LOG=${GOTO_FILE_LOG-/var/log/goto_http_redirect_server.log}
GOTO_FILE_SCRIPT=${GOTO_FILE_SCRIPT:-/usr/local/bin/goto_http_redirect_server}
GOTO_FILE_REDIRECTS=${GOTO_FILE_REDIRECTS:-/usr/local/share/goto_http_redirect_server.csv}
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
if [[ ! "${GOTO_ARGV[@]+x}" ]]; then
    declare -a GOTO_ARGV=()
fi

(declare -p | sort | grep 'GOTO_') || true
set -x
exec \
    ${sudoas} \
        ${authbind} \
            ${nice} \
                ${GOTO_FILE_SCRIPT} \
                    --redirects "${GOTO_FILE_REDIRECTS}" \
                    --ip "${GOTO_LISTEN_IP}" \
                    ${port} \
                    "${GOTO_PATH_STATUS_PARAMS[@]}" \
                    "${GOTO_PATH_RELOAD_PARAMS[@]}" \
                    --log "${GOTO_FILE_LOG}" \
                    ${debug} \
                    "${GOTO_ARGV[@]}"
