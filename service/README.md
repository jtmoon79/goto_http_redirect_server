Files for adding the _"Go To" HTTP Redirect Server_ as a Linux systemd service.

### Basic Instructions:

As `root` user,

#### HTTP redirects file

1. create a tab-separated values file (`'\t'`) with a list of HTTP redirects at
   path `/usr/local/share/goto_http_redirect_server.csv`

#### install files

    cp goto_http_redirect_server.sh /usr/local/bin/
    cp goto_http_redirect_server.service /etc/systemd/user/
    chmod +x /usr/local/bin/goto_http_redirect_server.sh
    chmod +x /etc/systemd/user/goto_http_redirect_server.service
    touch /usr/local/share/goto_http_redirect_server.csv
    pip install goto-http-redirect-server

systemd wrapper-script `goto_http_redirect_server.sh` expects pip to install to
`/usr/local/bin/goto_http_redirect_server`. See
[`goto_http_redirect_server.sh`](./goto_http_redirect_server.sh) for override
options.

#### enable and start systemd service

    systemctl enable /etc/systemd/user/goto_http_redirect_server.service    
    systemctl start goto_http_redirect_server.service

#### check service

    systemctl status goto_http_redirect_server.service

_Tested on Debian 9. MMV._
