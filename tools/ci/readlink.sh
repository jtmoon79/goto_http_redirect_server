#!/usr/bin/env bash
#
# portable readlink

set -e
set -u
set -o pipefail

python -B -c '\
import os
print(os.path.realpath(r""" '"${1}"' """[1:-1]))'
