#!/usr/bin/env bash
#
# Primitive self test of live running server (uses hardcoded sleeps).
# For basic sanity checks in CI systems.
# 
# 1. start the server
# 2. make some requests using `curl --fail`
# 3. wait for server to shutdown
#
# requires:
# - goto_http_redirect_server has been pip installed
# - curl

set -e
set -u
set -o pipefail

readonly PROGRAM_NAME='goto_http_redirect_server'
readonly LISTEN_IP='127.0.0.1'
readonly PORT=55923  # hopefully not in-use!
readonly URL="http://${LISTEN_IP}:${PORT}"
readonly PYTHON=${PYTHON-python}

set -x
curl --version  # note curl, fail sooner if not installed
which "${PROGRAM_NAME}"
"${PROGRAM_NAME}" --version
"${PYTHON}" --version
"${PYTHON}" -m "${PROGRAM_NAME}" --version
"${PROGRAM_NAME}" --debug \
    --shutdown 8 \
    --ip "${LISTEN_IP}" \
    --port ${PORT} \
    --from-to '/a' 'http://foo.com' \
    --status-path '/status' \
    --reload-path '/reload' \
    &

trap 'wait' EXIT

sleep 2

curl -v --fail --output /dev/null "${URL}/a"
curl -v --fail --output /dev/null "${URL}/status"
curl -v --fail --output /dev/null "${URL}/reload"
sleep 2
curl -v --fail --output /dev/null "${URL}/status"
curl -v --fail --output /dev/null "${URL}/reload"
