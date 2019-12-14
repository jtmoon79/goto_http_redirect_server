#!/usr/bin/env bash
#
# copy and chmod the systemd service files
# optionally, enable the service
#
# assumes goto_http_redirect_server has been installed and is in the $PATH
#
# usage:
#      service-install.sh [--enable] 

set -e
set -u

cd "$(dirname -- "${0}")/../.."

GOTO_FILE_REDIRECTS=/usr/local/share/goto_http_redirect_server.csv
GOTO_FILE_SCRIPT=/usr/local/bin/goto_http_redirect_server
GOTO_SYSTEMD_SH=/usr/local/bin/goto_http_redirect_server.sh
GOTO_CONFIG=/etc/goto_http_redirect_server.conf
GOTO_SERVICE=goto_http_redirect_server.service
GOTO_FILE_SERVICE=/etc/systemd/user/${GOTO_SERVICE}

# create redirects file
touch "${GOTO_FILE_REDIRECTS}"
chmod -v 0644 -- "${GOTO_FILE_REDIRECTS}"

# link goto_http_redirect_server
if which goto_http_redirect_server &>/dev/null; then
    ln -vs -- "$(which goto_http_redirect_server)" "${GOTO_FILE_SCRIPT}"
else
    cp -v -- ./goto_http_redirect_server/goto_http_redirect_server.py "${GOTO_FILE_SCRIPT}"
fi

# copy systemd wrapper
cp -v -- ./service/goto_http_redirect_server.sh "$(dirname -- "${GOTO_SYSTEMD_SH}")"
chmod -v 0755 -- "${GOTO_SYSTEMD_SH}"

# copy systemd wrapper configuration
cp -v -- ./service/goto_http_redirect_server.conf "${GOTO_CONFIG}"
chmod -v 0600 -- "${GOTO_CONFIG}"

# install systemd service
cp -v -- ./service/goto_http_redirect_server.service "$(dirname -- "${GOTO_FILE_SERVICE}")"
chmod -v 0444 -- "${GOTO_FILE_SERVICE}"

ls -l \
    "${GOTO_FILE_REDIRECTS}" \
    "${GOTO_FILE_SCRIPT}" \
    "${GOTO_SYSTEMD_SH}" \
    "${GOTO_CONFIG}" \
    "${GOTO_FILE_SERVICE}"

if [[ "${1:-}" == '--enable' ]]; then
    systemctl enable "${GOTO_FILE_SERVICE}"
fi
