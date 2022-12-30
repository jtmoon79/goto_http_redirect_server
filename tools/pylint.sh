#!/usr/bin/env bash
#
# run pylint with necessary settings
# XXX: currently, satisfying pylint is too difficult.
#      pylint is overly pedanctic, and disagrees with other static
#      checkers like mypy and flake8. pylint checking is only for curiousity.

set -e
set -u

cd "$(dirname -- "${0}")/.."

pylint --version
set -x
exec \
    pylint \
        --disable 'C0103' \
        goto_http_redirect_server/goto_http_redirect_server.py \
        setup.py \
        "${@}"
