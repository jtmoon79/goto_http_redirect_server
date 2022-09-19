#!/usr/bin/env bash
#
# update the goto_http_redirect_server when the input redirects file(s)
# change. This means edits to are immediately picked up by the server.

set -e
set -u

NAME=$(basename -- "${0}")
WATCHFILE_DEFAULT='/usr/local/share/goto_http_redirect_server.csv'
URL_GOTO_RELOAD_DEFAULT='http://localhost:80/reload'

if [[ "${1-}" == '--help' ]] || [[ "${1-}" == '-h' ]] || [[ "${1-}" == '-?' ]]; then
    echo "usage:
    ${NAME} [WATCHFILE [URL_GOTO_RELOAD]]

about:
    inotifywait a Redirects File WATCHFILE for goto_http_redirect_server process.
    When the Redirects File changes, HTTP GET to URL_GOTO_RELOAD. 

Parameters can be passed in the environment or command-line. Command-line
has precedence.

WATCHFILE defaults to '${WATCHFILE_DEFAULT}'
URL_GOTO_RELOAD defaults to '${URL_GOTO_RELOAD_DEFAULT}'
" >&2
    exit 1
fi

WATCHFILE=${1-${WATCHFILE-${WATCHFILE_DEFAULT}}}
URL_GOTO_RELOAD=${2-${URL_GOTO_RELOAD-${URL_GOTO_RELOAD_DEFAULT}}}
FLOCK_PID=

function log () {
    if ! which logger &>/dev/null; then
        return
    fi
    logger --id "${NAME}" --stderr "${*}"
}

function singleton () {
    # only one of this script running per $WATCHFILE
    # have flock hold the file forever
    echo "${PS4}flock --verbose --nonblock --no-fork --exclusive '${WATCHFILE}' -c 'sleep infinity'" >&2
    flock --nonblock --verbose --no-fork --exclusive "${WATCHFILE}" -c "sleep infinity" &
    FLOCK_PID=$!
    sleep 1
    # check flock process is running
    if ! kill -0 "${FLOCK_PID}" &>/dev/null; then
        echo "ERROR: another instance of '${NAME}' is holding flock on '${WATCHFILE}'" >&2
        exit 1
    fi
}

# check necessary programs are available
if ! which "inotifywait" &>/dev/null; then
    echo "ERROR: could not find program 'inotifywait'; probably in package inotify-tools" >&2
    exit 1
fi
if ! which "curl" &>/dev/null; then
    echo "ERROR: could not find program 'curl'" >&2
    exit 1
fi

singleton

function exit_ () {
    set -x
    kill "${FLOCK_PID}"
}
trap exit_ EXIT

function signal_goto_server () {
    if ! curl "${URL_GOTO_RELOAD}"; then
        log "ERROR: curl '${URL_GOTO_RELOAD}' failed."
        return 1
    fi
    #(
    #    set -x
    #    kill -SIGUSR1 "${GOTO_PID}"
    #)
}

# run forever
while sleep 1; do
    #if [[ ! -e "${WATCHFILE}" ]]; then
    #    log "File '${WATCHFILE}' does not exist! sleep 10…"
    #    sleep 10
    #    continue
    #fi
    (
        set -x
        inotifywait --event 'close_write' "${WATCHFILE}"
    )
    log "File '${WATCHFILE}' was updated!"
    sleep 2  # often there are clusters of write events so wait before signaling
    if ! signal_goto_server; then
        sleep 10
    fi
    echo >&2
done
exit 1
