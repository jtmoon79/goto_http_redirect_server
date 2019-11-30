Files for adding the _"Go To" HTTP Redirect Server_ as a Linux systemd service.

## Install Instructions

As `root` user,

### Create HTTP Redirects File

Create a tab-separated values file (`'\t'`) with a list of HTTP redirects at
path `/usr/local/share/goto_http_redirect_server.csv`

    touch /usr/local/share/goto_http_redirect_server.csv

This file is described in the top-level [README.md](./../README.md).

### Install Files

- `goto_http_redirect_server.sh`
  ```
  curl -o /usr/local/bin/goto_http_redirect_server.sh https://raw.githubusercontent.com/jtmoon79/goto_http_redirect_server/master/service/goto_http_redirect_server.sh
  chmod +x /usr/local/bin/goto_http_redirect_server.sh
  ```
  The wrapper-script expects the Python package to install to
  `/usr/local/bin/goto_http_redirect_server`.  The wrapper-script has options
  for environment variable overrides.

- `goto_http_redirect_server.service`
  ```
  curl -o /etc/systemd/user/goto_http_redirect_server.service https://raw.githubusercontent.com/jtmoon79/goto_http_redirect_server/master/service/goto_http_redirect_server.service
  chmod +x /etc/systemd/user/goto_http_redirect_server.service
  ```

- `goto_http_redirect_server`

  See top-level [README.md](./../README.md).

### Enable and Start systemd Service

    systemctl enable /etc/systemd/user/goto_http_redirect_server.service    
    systemctl start goto_http_redirect_server.service

### Check systemd Service

    systemctl status goto_http_redirect_server.service

_Tested on Debian 9. MMV._
