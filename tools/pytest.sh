#!/usr/bin/env bash
#
# run pytest with necessary settings

set -e
set -u

cd "$(dirname -- "${0}")/.."

export PYTHONPATH+=:"${PWD}"

python -m pytest --version
set -x
exec python \
        -m pytest \
            --verbose \
            -c ./.config/pytest.ini \
            --cov-config=./.config/coverage.ini \
            . \
