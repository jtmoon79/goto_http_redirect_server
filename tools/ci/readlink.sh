#!/usr/bin/env bash
#
# portable readlink

set -e
set -u
set -o pipefail

echo -n "${1}" | python -B -c '\
import os, sys
input_ = sys.stdin.read()
print(os.path.realpath(input_))'
