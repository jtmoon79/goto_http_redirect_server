
# Go To HTTP Redirect Server

[![CircleCI Build Status](https://circleci.com/gh/jtmoon79/goto_http_redirect_server.svg?style=svg)](https://circleci.com/gh/jtmoon79/goto_http_redirect_server)
[![Azure Build Status](https://dev.azure.com/jtmmoon/goto_http_redirect_server/_apis/build/status/jtmoon79.goto_http_redirect_server?branchName=master)](https://dev.azure.com/jtmmoon/goto_http_redirect_server/_build/latest?definitionId=1&branchName=master)
[![pytest-cov Code Coverage](https://img.shields.io/azure-devops/coverage/jtmmoon/goto_http_redirect_server/1)](https://dev.azure.com/jtmmoon/goto_http_redirect_server/_build?definitionId=1&_a=summary)
[![PyPI version](https://badge.fury.io/py/goto-http-redirect-server.svg)](https://badge.fury.io/py/goto-http-redirect-server)
[![Commits since](https://img.shields.io/github/commits-since/jtmoon79/goto_http_redirect_server/latest.svg)](https://img.shields.io/github/commits-since/jtmoon79/goto_http_redirect_server/latest.svg)
[![Python versions](https://img.shields.io/pypi/pyversions/goto-http-redirect-server.svg?longCache=True)](https://pypi.org/pypi/goto-http-redirect-server/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

The **_"Go To" HTTP Redirect Server_** for sharing dynamic shortcut URLs
on your network.

Trivial to install and run.  Only uses Python built-in modules.  Super handy 😄 ‼

----

<!-- python -m md_toc README.md github -->

- [Go To HTTP Redirect Server](#go-to-http-redirect-server)
  - [Install Manually](#install-manually)
  - [Install systemd Service](#install-systemd-service)
- [Use](#use)
  - [Gotchas](#gotchas)
  - [Live Reload](#live-reload)
    - [Reload via Signals](#reload-via-signals)
    - [Reload via browser](#reload-via-browser)
  - [systemd Service](#systemd-service)
  - [Pro Tips](#pro-tips)
- [`--help` message](#--help-message)

----

## Install Manually

1. create a tab-separated values file (`'\t'`) with a list of HTTP redirects.<br />
   Fields are "_from path_", "_to URL_", "_added by user_", and "_added on datetime_".<br />
   For example, given a file `./redirects1.csv`

       /bug	https://bugtracker.megacorp.local/view.cgi=${query}	alice	2019-08-10 00:05:10
       /hr	http://human-resources.megacorp.local/login	bob	2018-07-11 22:15:10
       /aws	https://us-west-2.console.aws.amazon.com/console/home?region=us-west-2#	carl	2019-01-05 12:35:10

2. Install (pick one)

    - pip install official release from pypi.org

          pip install goto-http-redirect-server

    - pip install latest code from github

          pip install "https://github.com/jtmoon79/goto_http_redirect_server/archive/master.zip"

    - Download from github and run

          curl "https://raw.githubusercontent.com/jtmoon79/goto_http_redirect_server/master/goto_http_redirect_server/goto_http_redirect_server.py"
          python goto_http_redirect_server.py --version

    - use [`pip-run`](https://pypi.org/project/pip-run/)

          pip-run --use-pep517 --quiet "git+https://github.com/jtmoon79/goto_http_redirect_server" -- \
              -m goto_http_redirect_server --version

    - Build and install using helper scripts [`tools/build-install.sh`](./tools/build-install.sh) or [`tools/build-install.ps1`](./tools/build-install.ps1)

          git clone "https://github.com/jtmoon79/goto_http_redirect_server.git"
          goto_http_redirect_server/tools/build-install.sh

    - Build and install

          git clone "https://github.com/jtmoon79/goto_http_redirect_server.git"
          cd goto_http_redirect_server
          python setup.py bdist_wheel
          python -m pip install --user ./dist/goto_http_redirect_server-*-py3-none-any.whl

3. start the _Go To HTTP Redirect Server_

        goto_http_redirect_server --redirects ./redirects1.csv

    or run as a module

        python -m goto_http_redirect_server --redirects ./redirects1.csv

    Requires at least Python version 3.5.2.

## Install systemd Service

See [service/README.md](./service/README.md).

# Use

From your browser, browse to a redirect path!  For example, given a network host
`goto` running `goto_http_redirect_server` on port `80`, and given the
example redirects file `./redirects1.csv` above, then<br />
in your browser, type **`goto/hr⏎`**. Your browser will end up at
**`http://human-resources.megacorp.local/login`** 😆‼<br />
Try  **`goto/bug?456⏎`**… shows bug 456 😝❗❗

## Gotchas

<small>

- Some browsers will assume a single word host, e.g. `goto/hr`, is a
  search engine query, i.e. the browser will query Google for "`goto/hr`".
  Type in a prepended http protocol, e.g. `http://goto/hr⏎`.\*\*

- In most corporate networks, a user's workstation will DNS search the corporate
  domain, e.g. `.local`.  This allows users to enter browser URL
  `goto/hr` which will resolve to host `goto.local`. Sometimes workstations
  do not search the corporate domain due to DNS Search Order setting not
  including `.local`. In that case, the user must specify the domain, e.g.
  instead of typing `goto/hr⏎`, the user must type `goto.local/hr⏎`.\*\*

\*\* _Mileage May Vary_ 😔

</small>

## Live Reload

When the tab-separated values files are modified, this program can reload them.
No service downtime!

### Reload via Signals

 1. Note during startup the Process ID (or query the host System).

 2. Send the process signal to the running `goto_http_redirect_server`.<br />
    In Unix, use `kill`.<br />
    In Windows, use [`windows-kill.exe`](https://github.com/alirdn/windows-kill/releases)<br />
    The running `goto_http_redirect_server` will re-read all files passed via
    `--redirects`.

### Reload via browser

1. Pass `--reload-path /reload` as a program command-line options.

2. Browse to `http://host/reload`.

## systemd Service

- See  [`service/`](./service) directory for systemd service files.

## Pro Tips

- Add a DNS addressable host on your network named `goto`. Run
  `goto_http_redirect_server` on the host.<br />
  Network users can type in their browser address bar `goto/…⏎` to easily use
  the _"Go To" HTTP Redirect Server_.\*\*

- There are many methods to secure a running process.
  One method is to use `authbind` to run `goto_http_redirect_server` as a low
  privilege process.

      apt install authbind
      touch /etc/authbind/byport/80
      chown nobody /etc/authbind/byport/80
      chmod 0500 /etc/authbind/byport/80
      sudo -u nobody -- authbind --deep python goto_http_redirect_server …

  This is an optional setting in [the systemd service](./service/).

<br />

----

# `--help` message

    usage: goto_http_redirect_server [--redirects REDIRECTS_FILES]
                                     [--from-to from to] [--ip IP] [--port PORT]
                                     [--status-path STATUS_PATH]
                                     [--reload-path RELOAD_PATH]
                                     [--redirect-code REDIRECT_CODE]
                                     [--field-delimiter FIELD_DELIMITER]
                                     [--status-note-file STATUS_NOTE_FILE]
                                     [--shutdown SHUTDOWN] [--log LOG] [--debug]
                                     [--version] [-?]

    The "Go To" HTTP Redirect Server for sharing dynamic shortcut URLs on your network.

    HTTP 308 Permanent Redirect reply server. Load this server with redirects of "from path" and
    "to URL" and let it run indefinitely. Reload the running server by signaling the
    process or HTTP requesting the RELOAD_PATH.

    Redirects:
      One or more required. May be passed multiple times.

      --redirects REDIRECTS_FILES
                            File of redirects. Within a file, is one redirect
                            entry per line. A redirect entry is four fields: "from
                            path", "to URL", "added by user", and "added on
                            datetime" separated by the FIELD_DELIMITER character.
      --from-to from to     A single redirect entry of "from path" and "to URL"
                            fields. For example, --from-to "/hr" "http://human-
                            resources.megacorp.local/login"

    Network Options:
      --ip IP, -i IP        IP interface to listen on. Default is 0.0.0.0 .
      --port PORT, -p PORT  IP port to listen on. Default is 80 .

    Server Options:
      --status-path STATUS_PATH
                            The status path dumps information about the process
                            and loaded redirects. Default status page path is
                            "/status".
      --reload-path RELOAD_PATH
                            Allow reloads by HTTP GET Request to passed URL Path.
                            e.g. --reload-path "/reload". May be a potential
                            security or stability issue. The program will always
                            allow reload by process signal. Default is off.
      --redirect-code REDIRECT_CODE
                            Set HTTP Redirect Status Code as an integer. Most
                            often the desired override will be 307 (Temporary
                            Redirect). Any HTTP Status Code could be used but odd
                            things will happen if a value like 500 is returned.
                            This Status Code is only returned when a loaded
                            redirect entry is found and returned. Default
                            successful redirect Status Code is 308 (Permanent
                            Redirect).
      --field-delimiter FIELD_DELIMITER
                            Field delimiter string for --redirects files per-line
                            redirect entries. Default is "\t" (ordinal 9).
      --status-note-file STATUS_NOTE_FILE
                            Status page note: Filesystem path to a file with HTML
                            that will be embedded within a <div> element in the
                            status page.
      --shutdown SHUTDOWN   Shutdown the server after passed seconds. Intended for
                            testing.
      --log LOG             Log to file at path LOG. Default logging is to
                            sys.stderr.
      --debug               Set logging level to DEBUG. Default logging level is
                            INFO.
      --version             Print "goto_http_redirect_server 1.1.2" and exit.
      -?, -h, --help        Print this help message and exit.

    About Redirect Entries:

      Entries found in --redirects file(s) and entries passed via --from-to are
      combined.
      Entries passed via --from-to override any matching "from path" entry found in
      redirects files.
      The "from path" field corresponds to the URI Path in the originating request.
      The "to URL" field corresponds to HTTP Header "Location" in the server
      Redirect reply.

      A redirects file entry has four fields separated by FIELD_DELIMITER character:
      "from path", "to URL", "added by user", "added on datetime".
      For example,

        /hr http://human-resources.megacorp.local/login     bob     2019-09-07 12:00:00

      The last two fields, "added by user" and "added on datetime", are intended
      for record-keeping within an organization.

      A passed redirect should have a leading "/" as this is the URI path given for
      processing.
      For example, the URL "http://host/hr" is processed as URI path "/hr".

      A redirect will combine the various incoming URI parts.
      For example, given redirect entry:

        /b  http://bug-tracker.megacorp.local/view.cgi      bob     2019-09-07 12:00:00

      And incoming GET or HEAD request:

        http://goto/b?id=123

      will result in a redirect URL:

        http://bug-tracker.megacorp.local/view.cgi?id=123

    Redirect Entry Template Syntax ("dynamic" URLs):

      Special substrings with Python string.Template syntax may be set in the
      redirect entry "To" field.

      First, given the URL

         http://host.com/pa/th;parm?a=A&b=B#frag

      the URI parts that form a urllib.urlparse ParseResult class would be:

        ParseResult(scheme='http', netloc='host.com', path='/pa/th',
                    params='parm', query='a=A&b=B', fragment='frag')

      So then given redirect entry:

        /b  http://bug-tracker.megacorp.local/view.cgi?id=${query}  bob     2019-09-07 12:00:00

      and the incoming GET or HEAD request:

        http://goto/b?123

      Substring '123' is the 'query' part of the ParseResult. The resultant redirect
      URL would become:

        http://bug-tracker.megacorp.local/view.cgi?id=123

    Redirect Entry Required Request Modifiers:

      Ending the Redirect Entry "from path" field with various URI separators allows
      preferences for which Redirect Entry to use. The purpose is to allow
      preferring a different Redirect Entry depending upon the users request.

      Given redirect entries:

        /b? http://bug-tracker.megacorp.local/view.cgi?id=${query}  bob     2019-09-07 12:00:00
        /b  http://bug-tracker.megacorp.local/main  bob     2019-09-07 12:00:00

      and the incoming GET or HEAD request:

        http://goto/b?123

      This will choose the first Redirect Entry and return 'Location' header

        http://bug-tracker.megacorp.local/view.cgi?id=123

      Whereas the incoming GET or HEAD request:

        http://goto/b

      This will choose the second Redirect Entry and return 'Location' header

        http://bug-tracker.megacorp.local/main

      The example combination sends a basic request for '/b' to some static page and
      a particular query request '/b?123' to a particular query path.
      Failed matches will "fallback" to the basic Redirect Entry, e.g. the Entry
      without any Required Request Modifiers.

      A Redirect Entry with Required Request Modifier will not match a request
      without such a modifier.

      Given redirect entries:

        /b? http://bug-tracker.megacorp.local/view.cgi?id=${query}  bob     2019-09-07 12:00:00

      and the incoming GET or HEAD request:

        http://goto/b

      will return 404 NOT FOUND.

      Required Request Modifiers must be at the end of the "from path" field string.
      Required Request Modifiers strings are:

         ';'  for user requests with a parameter.
         '?'  for user requests with a query.
         ';?' for user requests with a parameter and a query.

    About Redirect Files:

       A line with a leading "#" will be ignored.

    About Reloads:

      Sending a process signal to the running process will cause
      a reload of any files passed via --redirects.  This allows live updating of
      redirect information without disrupting the running server process.
      On Unix, the signal is SIGUSR1.  On Windows, the signal is SIGBREAK.
      On this system, the signal is Signals.SIGUSR1 (10).
      On Unix, use program `kill`.  On Windows, use program `windows-kill.exe`.

      A reload of redirect files may also be requested via passed URL path
      RELOAD_PATH.

    About Paths:

      Options --status-path and --reload-path may be passed paths to obscure access
      from unauthorized users. e.g.

          --status-path '/3811b8c6-a925-469e-a837-1787d4ade762'

    About this program:

      Modules used are available within the standard CPython distribution.
      Written for Python 3.7 but hacked to run with at least Python 3.5.2.

----

This project is released under [an MIT License granted by Dell Incorporated's
Open Source Project program](./LICENSE). All project contributions are entirely
reflective of the respective author(s) and not of Dell Inc.

Some portions of Javascript code in this project are subject to
[a separate MIT License](https://kryogenix.org/code/browser/licence.html).

<br />

<a href="https://stackexchange.com/users/216253/jamesthomasmoon1979"><img src="https://stackexchange.com/users/flair/216253.png" width="208" height="58" alt="profile for JamesThomasMoon1979 on Stack Exchange, a network of free, community-driven Q&amp;A sites" title="profile for JamesThomasMoon1979 on Stack Exchange, a network of free, community-driven Q&amp;A sites" /></a>
