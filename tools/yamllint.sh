#!/usr/bin/env bash
#
# run yamllint with necessary settings on found yaml files

set -e
set -u

cd "$(dirname -- "${0}")/.."

readonly YAMLCONFIG=./.config/yamllint.yml

yamllint --version

set -x

exec \
    yamllint \
        --config-file "${YAMLCONFIG}" \
        "./.azure-pipelines/azure-pipelines.yml" \
        "./.circleci/config.yml" \
        "./.config/yamllint.yml" \
        "${@}"
