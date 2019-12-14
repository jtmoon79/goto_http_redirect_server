#!/usr/bin/env bash
#
# run mypy with necessary settings

set -e
set -u

cd "$(dirname -- "${0}")/.."

python -m mypy --version
set -x
exec python \
        -m mypy \
            --config-file ./.config/mypy.ini \
            --warn-unused-configs \
            goto_http_redirect_server/goto_http_redirect_server.py
