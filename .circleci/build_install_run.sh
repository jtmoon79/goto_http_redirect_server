#!/usr/bin/env bash
# for CircleCI job build_install_run

set -e
set -u
set -o pipefail

cd "$(dirname -- "${0}")/.."  # cd to project top-level

set -x
whoami
pwd
env | sort
ls -la .
uname -a
python --version
pip --version
./build-install.sh --uninstall
