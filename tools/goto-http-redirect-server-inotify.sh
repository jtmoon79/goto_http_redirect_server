#!/usr/bin/env bash
#
# update the goto_http_redirect_server when the input redirects file(s)
# change. This means edits to are immediately picked up by the server.

set -e
set -u

# TODO: add usage
# TODO: parse as passed arguments
# TODO: can this behavior be folded into the .py file?

URL_GOTO_RELOAD=${1-${URL_GOTO_RELOAD-'http://localhost:80/reload'}}
WATCHFILE=${2-${WATCHFILE-'/usr/local/share/goto_http_redirect_server.csv'}}
NAME=$(basename -- "${0}")

function log () {
    logger --id "${NAME}" --stderr "${*}"
}

# check necessary programs are available
(set -x; which logger inotifywait curl)

# run forever
while sleep 5; do
    if [[ ! -e "${WATCHFILE}" ]]; then
        log "File '${WATCHFILE}' does not exist! Sleep 60..."
        sleep 60
        continue
    fi
    (
        set -x
        inotifywait --event 'close_write' "${WATCHFILE}"
    )
    log "File '${WATCHFILE}' was updated!"
    sleep 1  # often there are clusters of write events that occur, wait a bit
    curl "${URL_GOTO_RELOAD}" || (log "ERROR: curl '${URL_GOTO_RELOAD}' failed"; sleep 30;)
    echo >&2
done
