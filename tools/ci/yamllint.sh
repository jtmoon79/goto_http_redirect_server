#!/usr/bin/env bash
#
# run yamllint on all *.yml
# presumes yamllint is installed

set -e
set -u

cd "$(dirname -- "${0}")/../.."
YAMLCONFIG=./.config/yamllint.yaml

yamllint --version

for yaml in $(find \( -name '*.yml' -or -name '*.yml' \)); do
    (
        set -x 
        yamllint --config-file "${YAMLCONFIG}" "${yaml}"
    )
done
