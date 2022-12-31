#!/usr/bin/env sh
#
# Wrapper to update package management database on different systems.
# Helper for different CI environments.

set -e
set -u

if which apk 2>/dev/null 1>&2; then
    set -x
    exec apk update "${@}"
elif which yum 2>/dev/null 1>&2; then
    set -x
    exec yum update "${@}"
elif which apt 2>/dev/null 1>&2; then
    set -x
    exec apt update "${@}"
elif which zypper 2>/dev/null 1>&2; then
    set -x
    exec zypper update "${@}"
fi

echo "ERROR: cannot find a package manager to update." 1>&2
exit 1
