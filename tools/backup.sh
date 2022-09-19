#!/usr/bin/env bash
#
# backup.sh
#
# a quick manual backup script using 7zip
#

set -euo pipefail

cd "$(dirname "${0}")/.."

HERE="$(basename -- "$(realpath .)")"
ZIPFILE="../${HERE}-$(date '+%Y%m%dT%H%M%S')-$(hostname).zip"

Zz=$(which 7z)

(
set -x

"${Zz}" a -spf -bb1 -bt -stl -snl -tzip "${ZIPFILE}" \
    ./.azure-pipelines \
    ./.circleci \
    ./.config \
    ./.coverage \
    ./.gitignore \
    ./goto_http_redirect_server \
    ./goto-http-redirect-server.py \
    ./LICENSE \
    ./LICENSE-www.kryogenix.org \
    $(ls -d1 \
        ./pytest-cov-coverage_html \
        ./pytest-cov-coverage.xml \
        ./pytest-report.xml \
        2>/dev/null || true
    ) \
    ./README.md \
    ./service \
    ./setup.py \
    ./tools \

"${Zz}" l "${ZIPFILE}"
)

echo -e "\n\n\n"

ls -lh "${ZIPFILE}"
