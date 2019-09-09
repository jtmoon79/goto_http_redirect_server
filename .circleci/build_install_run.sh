#!/usr/bin/env bash
# for CircleCI job build_install_run

set -e
set -u
set -o pipefail

set -x
whoami
pwd
env | sort
ls -la .
uname -a
python --version
pip --version
"$(dirname -- "${0}")/../build-install.sh" --uninstall
