#!/usr/bin/env bash
#
# run flake8 with necessary settings

set -e
set -u

cd "$(dirname -- "${0}")/.."

flake8 --version
set -x
exec \
    flake8 \
        --config=./.config/flake8.ini \
        goto_http_redirect_server/goto_http_redirect_server.py \
        setup.py \
        "${@}"
