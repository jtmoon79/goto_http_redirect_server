#!/usr/bin/env bash
#
# run yamllint with necessary settings on found yaml files

set -e
set -u

cd "$(dirname -- "${0}")/.."

readonly YAMLCONFIG=./.config/yamllint.yml

yamllint --version

for yaml in $(find -maxdepth 3 -type f \( -name '*.yaml' -or -name '*.yml' \)); do
    (
        set -x 
        yamllint --config-file "${YAMLCONFIG}" "${yaml}"
    )
done
