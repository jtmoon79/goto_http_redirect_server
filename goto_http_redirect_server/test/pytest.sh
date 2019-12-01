#!/usr/bin/env sh
#
# run pytest for this directory

set -e
set -u

cd "$(dirname -- "${0}")/../.."

# dump versions informations
set -x
which python
python --version
python -m pytest --version
# run pytest of interest
exec python -m pytest -v ./goto_http_redirect_server/test/
