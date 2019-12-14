#!/usr/bin/env sh
#
# Wrapper to install a package in different Linux using the installed
# package manager. Helper for different CI environments.

set -e
set -u

if which apk 2>/dev/null 1>&2; then
    set -x
    exec apk add "${@}"
elif which yum 2>/dev/null 1>&2; then
    set -x
    exec yum install -y "${@}"
elif which apt 2>/dev/null 1>&2; then
    set -x
    exec apt install -y "${@}"
elif which zypper 2>/dev/null 1>&2; then
    set -x
    exec zypper install -y "${@}"
fi

echo "ERROR: cannot find a package manager; cannot install '${*}'" 1>&2
exit 1
