#!/usr/bin/env sh
#
# Wrapper to install a package in different Linux using the installed
# package manager. Helper for different CI environments.

set -e
set -u

if which apk 2>/dev/null 1>&2; then
    (
        set -x
        apk add "${@}"
    )
    exit
elif which yum 2>/dev/null 1>&2; then
    (
        set -x
        yum install -y "${@}"
    )
    exit
elif which apt 2>/dev/null 1>&2; then
    (
        set -x
        apt install -y "${@}"
    )
    exit
elif which zypper 2>/dev/null 1>&2; then
    (
        set -x
        zypper install -y "${@}"
    )
    exit
fi

echo "ERROR: cannot find a package manager; cannot install '${*}'" 1>&2
exit 1
