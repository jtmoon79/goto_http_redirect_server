#!/usr/bin/env sh
#
# Wrapper to update package management database on different systems.
# Helper for different CI environments.

set -e
set -u

if which apk 2>/dev/null 1>&2; then
    (
        set -x
        apk update
    )
    exit
elif which yum 2>/dev/null 1>&2; then
    (
        set -x
        yum update
    )
    exit
elif which apt 2>/dev/null 1>&2; then
    (
        set -x
        apt update
    )
    exit
elif which zypper 2>/dev/null 1>&2; then
    (
        set -x
        zypper update
    )
    exit
fi

echo "ERROR: cannot find a package manager to update." 1>&2
exit 1
