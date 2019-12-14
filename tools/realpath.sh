#!/usr/bin/env bash
#
# portable `realpath` (may not perfectly emulate error conditions)

set -e
set -u
set -o pipefail

python -B -c '\
import os
print(os.path.realpath(r""" '"${1}"' """[1:-1]))'
