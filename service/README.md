Files for adding the _"Go To" HTTP Redirect Server_ as a Linux systemd service.

### Basic Instructions:

As `root` user,

#### install files

    cp goto_http_redirect_server.sh /usr/local/bin/
    cp goto_http_redirect_server.service /etc/systemd/user/
    chmod +x /usr/local/bin/goto_http_redirect_server.sh
    chmod +x /etc/systemd/user/goto_http_redirect_server.service
    touch /usr/local/share/goto_http_redirect_server.csv
    pip install goto-http-redirect-server

#### enable and start systemd service

    systemctl enable /etc/systemd/user/goto_http_redirect_server.service    
    systemctl start goto_http_redirect_server.service

#### check service

    systemctl status goto_http_redirect_server.service

_Tested on Debian 9. MMV._
