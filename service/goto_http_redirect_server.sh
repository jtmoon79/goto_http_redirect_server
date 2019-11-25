#!/usr/bin/env bash
#
# systemd wrapper
#
# XXX: makes presumptions! needs work to be more portable!
# XXX: only tested on Debian 9

set -u
set -e
set -o pipefail


authbind=
sudoas=
debug=
port=

while getopts "au:p:dh?" opt; do
    case ${opt} in
        a)
            authbind='authbind --deep'
            ;;
        u)
            sudoas="sudo -u ${OPTARG} --"
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
                echo "Usage: ${0} [-a] [-u USER] [-p PORT] [-d]"
                echo
                echo "       -a  lower privilege using 'authbind --deep' (requires authbind)"
                echo "       -u  run process using 'sudo -u USER'  (requires sudo)"
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

IP_ADDR='0.0.0.0'
LOG="${TMP:-/var/log/}goto_http_redirect_server.log"
SCRIPT='/usr/local/bin/goto_http_redirect_server'
REDIRECTS_FILE='/usr/local/share/goto_http_redirect_server.csv'
PATH_STATUS='/'
PATH_RELOAD='/reload'

set -x
exec \
    ${sudoas} \
        ${authbind} \
            ${SCRIPT} \
                --redirects "${REDIRECTS_FILE}" \
                --ip "${IP_ADDR}" \
                ${port} \
                --status-path "${PATH_STATUS}" \
                --reload-path "${PATH_RELOAD}" \
                --log "${LOG}" \
                ${debug}
