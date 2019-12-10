#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# -*- pyversion: >=3.5.2 -*-


import argparse
from collections import defaultdict
import copy
import csv
import datetime
import getpass
import html
import http
from http import server
import json
import logging
import os
import pathlib
import pprint
import re
import signal
import socket
import socketserver
import sys
import threading
import time
import typing
from urllib import parse
import uuid


# canonical module informations used by setup.py
__version__ = '0.7.1'
__author__ = 'jtmoon79'
__url_project__ = 'https://github.com/jtmoon79/goto_http_redirect_server'
__url_pypi__ = 'https://pypi.org/project/goto-http-redirect-server/'
__url_issues__ = 'https://github.com/jtmoon79/goto_http_redirect_server/issues'
# first line of __doc__ is used in setup.py. Should match README.md and title at
# github.com project site.
__doc__ = """\
The "Go To" HTTP Redirect Server for sharing custom shortened HTTP URLs on \
your network.

Modules used are available within the standard CPython distribution.
Written for Python 3.7 but hacked to run with at least Python 3.5.2.
"""


#
# Types
#

# Redirect Entry types

Re_From = typing.NewType('Re_From', str)  # Redirect From URL Path
Re_To = typing.NewType('Re_To', str)  # Redirect To URL Location
Re_User = typing.NewType('Re_User', str)  # User that created the Redirect (records-keeping thing, does not affect behavior)
Re_Date = typing.NewType('Re_Date', datetime.datetime)  # Datetime Redirect was created (records-keeping thing, does not affect behavior)
Re_EntryKey = typing.NewType('Re_EntryKey', Re_From)
Re_EntryValue = typing.NewType('Re_EntryValue',
                               typing.Tuple[Re_To, Re_User, Re_Date])
Re_Entry_Dict = typing.NewType('Re_Entry_Dict',
                               typing.Dict[Re_EntryKey, Re_EntryValue])
Re_Field_Delimiter = typing.NewType('Re_Field_Delimiter', str)

# other helpful types

Path_List = typing.List[pathlib.Path]
FromTo_List = typing.List[typing.Tuple[str, str]]
Redirect_Counter = typing.DefaultDict[str, int]
Redirect_Code_Value = typing.NewType('Redirect_Code_Value', int)
str_None = typing.Union[str, None]
Path_None = typing.Union[pathlib.Path, None]


#
# globals and constants initialization
#

PROGRAM_NAME = 'goto_http_redirect_server'
IP_LISTEN = '0.0.0.0'
HOSTNAME = socket.gethostname()
TIME_START = time.time()
DATETIME_START = datetime.datetime.fromtimestamp(TIME_START)

# RedirectServer class things
SOCKET_LISTEN_BACKLOG = 30  # eventually passed to socket.listen
STATUS_PAGE_PATH_DEFAULT = '/status'
PATH_FAVICON = '/favicon.ico'
REDIRECT_PATHS_NOT_ALLOWED = (PATH_FAVICON,)
# HTTP Status Code used for redirects (among several possible redirect codes)
REDIRECT_CODE_DEFAULT = http.HTTPStatus.PERMANENT_REDIRECT
Redirect_Code = REDIRECT_CODE_DEFAULT
# urlparse-related things
RE_URI_KEYWORDS = re.compile(r'\${(path|params|query|fragment)}')
URI_KEYWORDS_REPL = ('path', 'params', 'query', 'fragment')
# signals
SIGNAL_RELOAD_UNIX = 'SIGUSR1'
SIGNAL_RELOAD_WINDOWS = 'SIGBREAK'
# signal to cause --redirects file reload
try:
    SIGNAL_RELOAD = signal.SIGUSR1  # Unix (not defined on Windows)
except AttributeError:
    SIGNAL_RELOAD = signal.SIGBREAK  # Windows (not defined on some Unix)
# redirect file things
FIELD_DELIMITER_DEFAULT = Re_Field_Delimiter('\t')
FIELD_DELIMITER_DEFAULT_NAME = 'tab'
FIELD_DELIMITER_DEFAULT_ESCAPED = FIELD_DELIMITER_DEFAULT.\
    encode('unicode_escape').decode('utf-8')
REDIRECT_FILE_IGNORE_LINE = '#'
# logging module initializations (call logging_init to complete)
LOGGING_FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S'
LOGGING_FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'
# importers can override 'log'
log = logging.getLogger(PROGRAM_NAME)
# write-once copy of sys.argv
sys_args = []  # type: typing.List[str]


#
# "volatile" global instances
#

# global list of --from-to passed redirects
Redirect_FromTo_List = []  # type: FromTo_List
# global list of --redirects files
Redirect_Files_List = []  # type: Path_List
reload = False
reload_datetime = datetime.datetime.now()  # set for mypy, will be set again
redirect_counter = defaultdict(int)  # type: typing.DefaultDict[str, int]
status_path = None
reload_path = None


#
# functions, classes, code
#


class StrDelay(object):
    """
    Delayed evaluation of object.__str__.
    Intended for logging messages that may not need to execute a passed function
    because the logging level may not be set.
    e.g.
       logging.debug('%s', complex_function(foo))
    The call to complex_function(foo) may not be necessary because logging.level
    might be logging.INFO. So skip the call to complex_function(foo) if it is
    not necessary, e.g.
       logging.debug('%s', StrDelay(complex_function, foo))

    XXX: There are probably more succinct implementations. Good enough.
    """
    def __init__(self, func, *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def __str__(self) -> str:
        #print('%s.__str__ of instance 0x%08X' %
        # (self.__class__.__name__, id(self)))
        out = ''
        if self._func:
            out = str(self._func(*self._args, **self._kwargs))
        return out


def html_escape(s_: str) -> str:
    return html.escape(s_)\
        .replace('\n', '<br />\n')\
        .replace('  ', r'&nbsp; ')


def html_a(href: str, text: str = '') -> str:
    """create HTML <a> from href URL"""
    if not text:
        text = href
    return '<a href="' + href + '">' + html_escape(text) + '</a>'


def combine_parseresult(pr1: parse.ParseResult, pr2: parse.ParseResult) -> str:
    """
    Combine parse.ParseResult parts.
    A parse.ParseResult example is
       parse.urlparse('http://host.com/path1;parmA=a,parmB=b?a=A&b=%20B&cc=CCC#FRAG')
    returns
        ParseResult(scheme='http', netloc='host.com', path='/path1',
                    params='parm2', query='a=A&b=%20B&ccc=CCC', fragment='FRAG')

    pr1 is assumed to represent a Re_To supplied at startup-time
    pr2 is assumed to be an incoming user request

    From pr1 use .scheme, .netloc, .path
    Prefer .fragment from pr2, then pr1
    Combine .params, .query

    The RedirectEntry 'To' can use string.Template syntax to replace with URI
    parts from pr1
    For example, given RedirectEntry supplied at start-time `pr1`
       /b	http://bugzilla.corp.local/search/bug.cgi?id=${query}	bob	
    A user incoming GET request for URL `pr2`
       'http://goto/b?123
    processed by `combine_parseresult` would become URL
       'http://bugzilla.corp.local/search/bug.cgi?id=123'

    Return a URL suitable for HTTP Header 'To'.

    XXX: this function is called for every request. It should be implemented
         more efficiently.
    XXX: This functions works fine for 98% of cases, but can get wonky with
         complicated pr1, pr2, and multiple repeating string.Template
         replacements.
    """

    # work from a OrderDict(pr2) instance, used to track what replacements
    # from pr2 have occurred
    pr2d = pr2._asdict()

    def ssub(val: str) -> str:
        """safe substitute val, if successful replacement then pop pr2d[key]"""
        # shortcut empty string case
        if not val:
            return val
        # shortcut when no Template syntax present
        if not RE_URI_KEYWORDS.search(val):
            return val
        # there are replacements to do
        remove = dict()
        for key in URI_KEYWORDS_REPL:
            repl = pr2d[key] if key in pr2d else key
            val_old = val
            val = re.sub(r'\${%s}' % key, repl, val)
            remove[key] = False
            if val != val_old:
                remove[key] = True
                #pr2d.pop(key)
            #log.debug('    "%s": "%s" -> "%s"  POP? %s', key, val_old, val, popd)
        for key, rm in remove.items():
            if rm and key in pr2d:
                pr2d.pop(key)
        return val

    # starting with a copy of pr1 with safe_substitutes
    pr = dict()
    for k_, v_ in pr1._asdict().items():
        pr[k_] = ssub(v_)

    # selectively combine URI parts from pr2d
    # safe_substitute where appropriate
    if 'fragment' in pr2d and pr2d['fragment']:
        pr['fragment'] = pr2d['fragment']
    if 'params' in pr2d and pr2d['params']:
        if pr1.params:
            # XXX: how are URI Object Parameters combined?
            #      see https://tools.ietf.org/html/rfc1808.html#section-2.1
            pr['params'] = ssub(pr1.params) + ';' + pr2d['params']
        else:
            pr['params'] = pr2d['params']
    if 'query' in pr2d and pr2d['query']:
        if pr1.query:
            pr['query'] = ssub(pr1.query) + '&' + pr2d['query']
        else:
            pr['query'] = pr2d['query']

    url = parse.urlunparse(parse.ParseResult(**pr))
    return url


def logging_init(debug: bool, filename: Path_None) -> None:
    """initialize logging module to my preferences"""

    global LOGGING_FORMAT
    filename_ = str(filename.absolute()) if filename else None
    logging.basicConfig(
        filename=filename_,
        level=logging.DEBUG,
        format=LOGGING_FORMAT,
        datefmt=LOGGING_FORMAT_DATETIME
    )
    global log
    log = logging.getLogger(PROGRAM_NAME)
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)


def print_debug(message: str, end: str = '\n', file=sys.stderr) -> None:
    """
    Helper for printing (preferably to stderr) and checking logging.DEBUG.
    Sometimes a full logging message is too much.
    """
    if log.level <= logging.DEBUG:
        print(message, end=end, file=file)
        if hasattr(file, 'flush'):
            file.flush()


def fromisoformat(dts: str) -> datetime.datetime:
    """
    Call datetime.datetime.fromisoformat on input string.
    ISO 8901 Date Time format looks like
    '2019-07-01 01:20:33' or '2019-07-01T01:20:33'

    Versions of Python < 3.7 do not have datetime.datetime.fromisoformat so
    provide an extremely basic implementation.
    Could use https://pypi.org/project/backports-datetime-fromisoformat/
    but this program goal is to avoid 3rd party modules.
      '2019-07-01 01:20:33'
       0123456789012345678
    """

    def _fromisoformat_impl(s_: str) -> datetime.datetime:
        return datetime.datetime(
            int(s_[0:4]),  # year
            month=int(s_[5:7]),
            day=int(s_[8:10]),
            hour=int(s_[11:13]),
            minute=int(s_[14:16]),
            second=int(s_[17:19])
        )

    _fromisoformat = _fromisoformat_impl
    if hasattr(datetime.datetime, 'fromisoformat'):
        _fromisoformat = datetime.datetime.fromisoformat  # type: ignore

    try:
        dt = _fromisoformat(dts)
    except ValueError:
        log.error('bad datetime input (%s), fallback to program start datetime',
                  dts)
        dt = DATETIME_START
    return dt


def redirect_handler_factory(redirects: Re_Entry_Dict,
                             status_code: http.HTTPStatus,
                             status_path_: str,
                             reload_path_: str_None):
    """
    :param redirects: dictionary of from-to redirects for the server
    :param status_code: HTTPStatus instance to use for successful redirects
    :param status_path_: server status page path
    :param reload_path_: reload request path
    :return: RedirectHandler type: request handler class type for
             RedirectServer.RequestHandlerClass
    """

    log.debug('using redirect dictionary (0x%08x) with %s entries:\n%s',
              id(redirects), len(redirects.keys()),
              StrDelay(pprint.pformat, redirects, indent=2)
    )

    class RedirectHandler(server.SimpleHTTPRequestHandler):

        Header_Server_Host = ('Redirect-Server-Host', HOSTNAME)
        Header_Server_Version = ('Redirect-Server-Version', __version__)

        def log_message(self, format_, *args, **kwargs):
            """
            override the RedirectHandler.log_message so RedirectHandler
            instances use the module-level logging.Logger instance `log`
            """
            try:
                prepend = str(self.client_address[0]) + ':' + \
                           str(self.client_address[1]) + ' '
                if 'loglevel' in kwargs and \
                   isinstance(kwargs['loglevel'], type(log.level)):
                    log.log(kwargs['loglevel'], prepend + format_, *args)
                    return
                log.debug(prepend + format_, *args)
            except Exception as ex:
                print('Error during log_message\n%s' % str(ex), file=sys.stderr)

        def _write_html_doc(self, html_doc: str) -> None:
            """
            Write out the HTML document and required headers.
            This calls end_headers!
            """
            # From https://tools.ietf.org/html/rfc2616#section-14.13
            #      The Content-Length entity-header field indicates the size of
            #      the entity-body, in decimal number of OCTETs
            # XXX: does this follow *all* Message Length rules?
            #      https://tools.ietf.org/html/rfc2616#section-4.4
            html_docb = bytes(html_doc,
                              encoding='utf-8',
                              errors='xmlcharrefreplace')
            self.send_header('Content-Length', str(len(html_docb)))
            self.end_headers()
            self.wfile.write(html_docb)
            return

        def do_GET_status(self) -> None:
            """dump status information about this server instance"""

            http_sc = http.HTTPStatus.OK  # HTTP Status Code
            self.log_message('status requested, returning %s (%s)',
                             int(http_sc), http_sc.phrase,
                             loglevel=logging.INFO)
            self.send_response(http_sc)
            self.send_header(*self.Header_Server_Host)
            self.send_header(*self.Header_Server_Version)
            he = html_escape  # abbreviate

            # create the html body
            esc_title = he(
                '%s status' % PROGRAM_NAME)
            start_datetime = datetime.datetime.\
                fromtimestamp(TIME_START).replace(microsecond=0)
            uptime = time.time() - TIME_START
            esc_overall = \
                'Program {}'.format(
                    html_a(__url_project__, PROGRAM_NAME)
                )
            esc_overall += he(' version {}.\n'.format(__version__))
            esc_overall += he(
                'Process ID %s listening on %s:%s on host %s\n'
                'Process start datetime %s (up time %s)\n'
                'Successful Redirect Status Code is %s (%s)'
                % (os.getpid(), self.server.server_address[0],
                   self.server.server_address[1], HOSTNAME,
                   start_datetime, datetime.timedelta(seconds=uptime),
                   int(status_code), status_code.phrase,)
            )
            esc_reload_datetime = he(reload_datetime.isoformat())

            def obj_to_html(obj, sort_keys=False) -> str:
                """Convert an object to html"""
                return he(
                    json.dumps(obj, indent=2, ensure_ascii=False,
                               sort_keys=sort_keys, default=str)
                    # pprint.pformat(obj)
                )

            def redirects_to_html(rd: Re_Entry_Dict) -> str:
                """Convert Re_Entry_Dict linkable html"""
                s_ = he('{\n')
                for key in rd.keys():
                    val = rd[key]
                    s_ += he('  "') + html_a(key) + he('": [\n')
                    s_ += he('    "') + html_a(val[0]) + he('",\n')
                    s_ += he('    "%s",\n' % val[1])
                    s_ += he('    "%s"\n' % val[2])
                    s_ += he('  ]\n')
                s_ += he('\n}')
                return s_

            esc_reload_info = he(
                ' (process signal %d (%s))' % (SIGNAL_RELOAD, SIGNAL_RELOAD)
            )
            esc_redirects_counter = obj_to_html(redirect_counter)
            esc_redirects = redirects_to_html(redirects)
            esc_files = obj_to_html(Redirect_Files_List)
            html_doc = """\
<!DOCTYPE html>
<html lang="en">
  <head>
  <meta charset="utf-8"/>
  <title>{esc_title}</title>
  </head>
  <body>
    <div>
        <h3>Process Information:</h3>
        <pre>
{esc_overall}
        </pre>
    </div>
    <div>
        <h3>Redirects Counter:</h3>
        Counting of successful redirect responses:
        <pre>
{esc_redirects_counter}
        </pre>
        <h3>Currently Loaded Redirects:</h3>
        Last Reload Time {esc_reload_datetime}
        <pre>
{esc_redirects}
        </pre>
    </div>
    <div>
        <h3>Redirect Files Searched During an Reload{esc_reload_info}:</h3>
        <pre>
{esc_files}
        </pre>
    </div>
  </body>
</html>\
"""\
                .format(esc_title=esc_title,
                        esc_overall=esc_overall,
                        esc_redirects_counter=esc_redirects_counter,
                        esc_reload_datetime=esc_reload_datetime,
                        esc_redirects=esc_redirects,
                        esc_reload_info=esc_reload_info,
                        esc_files=esc_files)
            self._write_html_doc(html_doc)
            return

        def do_GET_reload(self) -> None:
            http_sc = http.HTTPStatus.ACCEPTED  # HTTP Status Code
            self.log_message('reload requested, returning %s (%s)',
                             int(http_sc), http_sc.phrase,
                             loglevel=logging.INFO)
            esc_datetime = html_escape(datetime.datetime.now().isoformat())
            self.send_response(http_sc)
            self.send_header(*self.Header_Server_Host)
            self.send_header(*self.Header_Server_Version)
            esc_title = html_escape('%s reload' % PROGRAM_NAME)
            html_doc = """\
<!DOCTYPE html>
<html lang="en">
  <head>
  <meta charset="utf-8"/>
  <title>{esc_title}</title>
  </head>
  <body>
    Reload request accepted at {esc_datetime}.
  </body>
</html>\
"""\
            .format(esc_title=esc_title, esc_datetime=esc_datetime)
            self._write_html_doc(html_doc)
            global reload
            reload = True
            return

        def do_GET_redirect_NOT_FOUND(self, path: str) -> None:
            """a Redirect request was not found, return some HTML to the user"""

            self.send_response(http.HTTPStatus.NOT_FOUND)
            self.send_header(*self.Header_Server_Host)
            self.send_header(*self.Header_Server_Version)
            esc_title = html_escape("Not Found - '%s'" % path[:64])
            esc_path = html_escape(path)
            html_doc = """\
<!DOCTYPE html>
<html lang="en">
  <head>
  <meta charset="utf-8"/>
  <title>{esc_title}</title>
  </head>
  <body>
    Redirect Path not found: <code>{esc_path}</code>
  </body>
</html>\
"""\
            .format(esc_title=esc_title,
                    esc_path=esc_path)
            self._write_html_doc(html_doc)
            return

        def do_GET_redirect(self,
                            parseresult: parse.ParseResult,
                            redirects_: Re_Entry_Dict) -> None:
            """
            handle the HTTP Redirect Request (the entire purpose of this
            script)
            """

            if parseresult.path not in redirects_.keys():
                self.log_message(
                    'no redirect found for (%s), returning %s (%s)',
                    parseresult.path,
                    int(http.HTTPStatus.NOT_FOUND),
                    http.HTTPStatus.NOT_FOUND.phrase,
                    loglevel=logging.INFO)
                return self.do_GET_redirect_NOT_FOUND(parseresult.path)

            key = Re_EntryKey(Re_From(parseresult.path))
            # merge RedirectEntry URI parts with incoming requested URI parts
            to_parsed = parse.urlparse(redirects_[key][0])
            to = combine_parseresult(to_parsed, parseresult)
            user = redirects_[key][1]
            dt = redirects_[key][2]

            self.log_message('redirect found (%s) → (%s), returning %s (%s)',
                             key, to,
                             int(status_code), status_code.phrase,
                             loglevel=logging.INFO)

            self.send_response(status_code)
            # The 'Location' Header is used by browsers for HTTP 30X Redirects
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Location
            self.send_header(*self.Header_Server_Host)
            self.send_header(*self.Header_Server_Version)
            # the most important statement in this program
            self.send_header('Location', to)
            try:
                self.send_header('Redirect-Created-By', user)
            except UnicodeEncodeError:
                log.exception('header "Redirect-Created-By" set to fallback')
                self.send_header('Redirect-Created-By', 'Error Encoding User')
            self.send_header('Redirect-Created-Date', dt.isoformat())
            # TODO: https://tools.ietf.org/html/rfc2616#section-10.3.2
            #       the entity of the response SHOULD contain a short hypertext
            #       note with a hyperlink to the new URI(s)
            self.send_header('Content-Length', '0')
            self.end_headers()
            # Do Not Write HTTP Content
            count_key = '(%s) → (%s)' % (parseresult.path, to)
            redirect_counter[count_key] += 1
            return

        def do_GET(self) -> None:
            """invoked per HTTP GET Request"""
            print_debug('')
            try:
                self.log_message(
                    'self: %s (0x%08X)\nself.client_address: %s\n'
                    'self.command: %s\nself.path: "%s"\n'
                    'self.headers:\n  %s',
                    type(self), id(self), self.client_address,
                    self.command, self.path,
                    str(self.headers).strip('\n').replace('\n', '\n  '),
                )
            except:
                log.exception('Failed to log GET request')

            parseresult = parse.urlparse(self.path)
            if parseresult.path == status_path_:
                self.do_GET_status()
                return
            elif parseresult.path == reload_path_:
                self.do_GET_reload()
                return

            self.do_GET_redirect(parseresult, redirects)
            return

    return RedirectHandler


def load_redirects_fromto(from_to: FromTo_List) -> Re_Entry_Dict:
    """
    create Re_Entry for each --from-to passed
    :return: Re_Entry_Dict
    """

    user = getpass.getuser()
    now = datetime.datetime.now()
    entrys = Re_Entry_Dict({})
    for tf in from_to:
        entrys[Re_EntryKey(Re_From(tf[0]))] = \
            Re_EntryValue((Re_To(tf[1]), Re_User(user), Re_Date(now),))
    return entrys


def load_redirects_files(redirects_files: Path_List,
                         field_delimiter: Re_Field_Delimiter) \
        -> Re_Entry_Dict:
    """
    :param redirects_files: list of file paths to process for Re_Entry
    :param field_delimiter: passed to csv.reader keyword delimiter
    :return: Re_Entry_Dict of file line items converted to Re_Entry
    """

    entrys = Re_Entry_Dict({})

    # create Entry for each line in passed redirects_files
    for rfilen in redirects_files:
        try:
            log.info('Process File (%s)', rfilen)
            with open(str(rfilen), 'r', encoding='utf-8') as rfile:
                csvr = csv.reader(rfile, delimiter=field_delimiter)
                for row in csvr:
                    try:
                        log.debug('File Line (%s:%s):%s',
                                  rfilen, csvr.line_num, row)
                        if not row:  # skip empty row
                            continue
                        if row[0].startswith(REDIRECT_FILE_IGNORE_LINE):
                            # skip rows starting with such
                            continue
                        from_path = row[0]
                        to_url = row[1]
                        user_added = row[2]
                        date_added = row[3]
                        # ignore remaining fields
                        dt = fromisoformat(date_added)
                        entrys[Re_EntryKey(Re_From(from_path))] = \
                            Re_EntryValue((
                                Re_To(to_url),
                                Re_User(user_added),
                                Re_Date(dt),)
                            )
                    except Exception:
                        log.exception('Error processing row %d of file %s',
                                      csvr.line_num, rfilen)
        except Exception:
            log.exception('Error processing file %s', rfilen)

    return entrys


def clean_redirects(entrys_files: Re_Entry_Dict) -> Re_Entry_Dict:
    """remove entries with To paths that are reserved or cannot be encoded"""

    # TODO: process re_entry for circular loops of redirects, either
    #       break those loops or log.warning
    #       e.g. given redirects '/a' → '/b' and '/b' → '/a',
    #       the browser will (in theory) redirect forever.
    #       (browsers I tested force stopped the redirect loop; Edge, Chrome).

    for path in REDIRECT_PATHS_NOT_ALLOWED:
        re_key = Re_EntryKey(Re_From(path))
        if re_key in entrys_files.keys():
            log.warning(
                'Removing reserved From value "%s" from redirect entries.',
                path
            )
            entrys_files.pop(re_key)

    # check for To "Location" Header values that will fail to encode
    remove = []
    for re_key in entrys_files.keys():
        # test "Location" header value before send_response(status_code)
        to = entrys_files[re_key][0]
        try:
            # this is done in standard library http/server.py
            # method BaseServer.send_header
            to.encode('latin-1', 'strict')
        except UnicodeEncodeError:
            log.warning(
                'Removing To "Location" value "%s"; it fails encoding to "latin-1"',
                to
            )
            remove.append(re_key)
    for re_key in remove:
        entrys_files.pop(re_key)

    return entrys_files


def load_redirects(from_to: FromTo_List,
                   redirects_files: Path_List,
                   field_delimiter: Re_Field_Delimiter) \
        -> Re_Entry_Dict:
    """
    load (or reload) all redirect information, process into Re_EntryList
    Remove bad entries.
    :param from_to: list --from-to passed redirects for Re_Entry
    :param redirects_files: list of files to process for Re_Entry
    :param field_delimiter: field delimiter within passed redirects_files
    :return: Re_Entry_Dict: all processed information
    """
    entrys_fromto = load_redirects_fromto(from_to)
    entrys_files = load_redirects_files(redirects_files, field_delimiter)
    entrys_files.update(entrys_fromto)

    entrys_files = clean_redirects(entrys_files)

    return entrys_files


class RedirectServer(socketserver.ThreadingTCPServer):
    """
    Custom Server to allow reloading redirects while serve_forever.
    """
    field_delimiter = FIELD_DELIMITER_DEFAULT

    def __init__(self, *args):
        """adjust parameters of the Parent class"""
        super().__init__(*args)
        self.block_on_close = False
        self.request_queue_size = SOCKET_LISTEN_BACKLOG
        self.timeout = 5

    def __enter__(self):
        """Python version <= 3.5 does not implement BaseServer.__enter__"""
        if hasattr(socketserver.TCPServer, '__enter__'):
            return super(socketserver.TCPServer, self).__enter__()
        """copy+paste from Python 3.7 socketserver.py class BaseServer"""
        return self

    def __exit__(self, *args):
        """Python version <= 3.5 does not implement BaseServer.__exit__"""
        if hasattr(socketserver.TCPServer, '__exit__'):
            return super(socketserver.TCPServer, self).__exit__()
        """copy+paste from Python 3.7 socketserver.py class BaseServer"""
        self.server_close()

    def shutdown(self):
        """helper to allow others to know when shutdown was called"""
        self._shutdown = True
        return super(socketserver.TCPServer, self).shutdown()

    def service_actions(self):
        """
        Override function.

        Polled during socketserver.TCPServer.serve_forever.
        Checks global reload and create new handler (which will re-read
        the Redirect_Files_List)

        TODO: avoid use of globals, somehow pass instance variables to this
              function or class instance
        """

        #print_debug('.', end='')
        super(RedirectServer, self).service_actions()

        global reload
        if not reload:
            return
        reload = False
        global Redirect_FromTo_List
        global Redirect_Files_List
        entrys = load_redirects(Redirect_FromTo_List,
                                Redirect_Files_List,
                                self.field_delimiter)
        global status_path
        global reload_datetime
        global reload_path
        # distracting to read microsecond, set to 0
        reload_datetime = datetime.datetime.now().replace(microsecond=0)
        redirect_handler = redirect_handler_factory(entrys,
                                                    Redirect_Code,
                                                    status_path,
                                                    reload_path)
        pid = os.getpid()
        log.debug(
            "reload %s (0x%08x)\n"
            "new RequestHandlerClass (0x%08x) to replace old (0x%08x)\n"
            "PID %d",
            reload, id(reload),
            id(redirect_handler), id(self.RequestHandlerClass),
            pid
        )

        self.RequestHandlerClass = redirect_handler


def reload_signal_handler(signum, _) -> None:
    """
    Catch signal and set global reload (which is checked elsewhere)
    :param signum: signal number (int)
    :param _: Python frame (unused)
    :return: None
    """
    global reload
    log.debug(
        'reload_signal_handler: Signal Number %s, reload %s (0x%08x)',
        signum, reload, id(reload))
    reload = True


def process_options() -> typing.Tuple[str,
                                      int,
                                      bool,
                                      Path_None,
                                      str,
                                      str,
                                      Redirect_Code_Value,
                                      int,
                                      Re_Field_Delimiter,
                                      FromTo_List,
                                      typing.List[str]]:
    """Process script command-line options."""

    rcd = REDIRECT_CODE_DEFAULT  # abbreviate
    global sys_args
    sys_args = copy.copy(sys.argv)  # set once

    parser = argparse.ArgumentParser(
        description="""\
The "Go To" HTTP Redirect Server! For sharing custom shortened HTTP URLs on \
your network.

HTTP %s %s reply server. Load this server with redirects of "from path" and
"to URL" and let it run indefinitely. Reload the running server by signaling the
process or HTTP requesting the RELOAD_PATH.
"""
                    % (int(rcd), rcd.phrase),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog=PROGRAM_NAME,
        add_help=False
    )
    pgroup = parser.add_argument_group(title='Redirects',
                                       description='One or more required.'
                                       ' May be passed multiple times.')
    pgroup.add_argument('--redirects', dest='redirects_files', action='append',
                        help='File of redirects. Within a file,'
                        ' is one redirect entry per line. A redirect entry is '
                        ' four fields:'
                        ' "from path", "to URL", "added by user", and'
                        ' "added on datetime"'
                        ' separated by the FIELD_DELIMITER character.',
                        default=list())
    pgroup.add_argument('--from-to',
                        nargs=2, metavar=('from', 'to'),
                        action='append',
                        help='A single redirect entry of "from path" and'
                             ' "to URL" fields. For example,'
                             ' --from-to "/hr" "http://human-resources.mycorp.local/login"',
                        default=list())

    pgroup = parser.add_argument_group(title='Network Options')
    pgroup.add_argument('--ip', '-i', action='store', default=IP_LISTEN,
                        help='IP interface to listen on.'
                             ' Default is %(default)s .')
    pgroup.add_argument('--port', '-p', action='store', type=int, default=80,
                        help='IP port to listen on.'
                             ' Default is %(default)s .')

    pgroup = parser.add_argument_group(title='Server Options')
    pgroup.add_argument('--status-path', action='store',
                        default=STATUS_PAGE_PATH_DEFAULT, type=str,
                        help=' The status path'
                             ' dumps information about the process and loaded'
                             ' redirects.'
                             ' Default status page path is "%(default)s".')
    pgroup.add_argument('--reload-path', action='store',
                        default=None, type=str,
                        help='Allow reloads by HTTP GET Request to passed URL'
                             ' Path. e.g. --reload-path "/reload".'
                             ' May be a potential security or stability issue.'
                             ' The program will always allow reload by'
                             ' process signal.'
                             ' Default is off.')
    rc_302 = http.HTTPStatus.TEMPORARY_REDIRECT
    pgroup.add_argument('--redirect-code', action='store',
                        default=int(rcd), type=int,
                        help='Set HTTP Redirect Status Code as an'
                             ' integer. Most often the desired override will'
                             ' be ' + str(int(rc_302)) + ' (' + rc_302.phrase +
                             '). Any HTTP Status Code could be used but odd'
                             ' things will happen if a value like 500 is'
                             ' returned.'
                             ' This Status Code is only returned when a'
                             ' loaded redirect entry is found and returned.'
                             ' Default successful redirect Status Code is'
                             ' %(default)s (' + rcd.phrase + ').')
    pgroup.add_argument('--field-delimiter', action='store',
                        default=FIELD_DELIMITER_DEFAULT,
                        help=(
                             'Field delimiter string for --redirects files'
                             ' per-line redirect entries.'
                             ' Default is "' + FIELD_DELIMITER_DEFAULT_ESCAPED +
                             '" (ordinal ' +
                             str(ord(FIELD_DELIMITER_DEFAULT[0])) + ').'
                             ))
    assert len(FIELD_DELIMITER_DEFAULT) == 1,\
        '--help is wrong about default FIELD_DELIMITER'
    pgroup.add_argument('--shutdown', action='store', type=int,
                        default=0,
                        help='Shutdown the server after passed seconds.'
                             ' Intended for testing.')
    pgroup.add_argument('--log', action='store', type=str, default=None,
                        help='Log to file at path LOG.'
                             ' Default logging is to sys.stderr.')
    pgroup.add_argument('--debug', action='store_true', default=False,
                        help='Set logging level to DEBUG.'
                             ' Default logging level is INFO.')
    pgroup.add_argument('--version', action='version',
                        help='Print "%s %s" and exit.' %
                             (PROGRAM_NAME, __version__),
                        version='%(prog)s ' + __version__)
    pgroup.add_argument('-?', '-h', '--help', action='help',  # add last
                        help='Print this help message and exit.')

    parser.epilog = """
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

    /hr{fd}http://human-resources.mycorp.local/login{fd}bob{fd}2019-09-07 12:00:00

  The last two fields, "added by user" and "added on datetime", are intended
  for record-keeping within an organization.

  A passed redirect should have a leading "/" as this is the URI path given for
  processing.
  For example, the URL "http://host/hr" is processed as URI path "/hr".

  A redirect will combine the various incoming URI parts.
  For example, given redirect entry:

    /b{fd}http://bug-tracker.mycorp.local/view.cgi{fd}bob{fd}2019-09-07 12:00:00

  And incoming request:

    http://goto/b?id=123

  will result in a redirect URL:

    http://bug-tracker.mycorp.local/view.cgi?id=123

Redirect Entry Template Syntax:

  Special substrings with Python string.Template syntax may be set in the
  redirect entry "To" field.

  First, given the URL

     http://host.com/path;parm?a=A&b=B#frag

  the URI parts that form a urllib.urlparse ParseResult class would be:

    ParseResult(scheme='http', netloc='host.com', path='/path',
                params='parm', query='a=A&b=B', fragment='frag')

  So then given redirect entry:

    /b{fd}http://bug-tracker.mycorp.local/view.cgi?id=${query}{fd}bob{fd}2019-09-07 12:00:00

  and the incoming request:

    http://goto/b?123

  Substring '123' is the 'query' part of the ParseResult. The resultant redirect
  URL would become:

    http://bug-tracker.mycorp.local/view.cgi?id=123

About Redirect Files:

   A line with a leading "{ignore}" will be ignored.

About Reloads:

  Sending a process signal to the running process will cause
  a reload of any files passed via --redirects.  This allows live updating of
  redirect information without disrupting the running server process.
  On Unix, the signal is {sig_unix}.  On Windows, the signal is {sig_win}.
  On this system, the signal is {sig_here} ({sig_hered:d}).
  On Unix, use program `kill`.  On Windows, use program `windows-kill.exe`.

  A reload of redirect files may also be requested via passed URL path
  RELOAD_PATH.

About Paths:

  Options --status-path and --reload-path may be passed paths to obscure access
  from unauthorized users. e.g.

      --status-path '/{rand1}'

""".format(
        fd=FIELD_DELIMITER_DEFAULT,
        sig_unix=SIGNAL_RELOAD_UNIX, sig_win=SIGNAL_RELOAD_WINDOWS,
        sig_here=str(SIGNAL_RELOAD), sig_hered=int(SIGNAL_RELOAD),
        ignore=REDIRECT_FILE_IGNORE_LINE,
        query='{query}',
        rand1=str(uuid.uuid4()),
       )

    args = parser.parse_args()

    if not (args.redirects_files or args.from_to):
        print('ERROR: No redirect information was passed (--redirects or '
              '--from-to)',
              file=sys.stderr)
        parser.print_usage()
        sys.exit(1)

    if args.status_path == args.reload_path:
        print('ERROR: --status-path and --reload-path must be different paths',
              file=sys.stderr)
        parser.print_usage()
        sys.exit(1)

    log_filename = None
    if args.log:
        log_filename = pathlib.Path(args.log)

    redirects_files = args.redirects_files  # type: typing.List[str]
    return \
        str(args.ip), \
        int(args.port), \
        bool(args.debug), \
        log_filename, \
        str(args.status_path), \
        str(args.reload_path), \
        Redirect_Code_Value(args.redirect_code), \
        int(args.shutdown),\
        Re_Field_Delimiter(args.field_delimiter), \
        args.from_to, \
        redirects_files


def main() -> None:
    ip, \
        port, \
        log_debug, \
        log_filename, \
        status_path_, \
        reload_path_, \
        redirect_code_, \
        shutdown, \
        field_delimiter, \
        from_to, \
        redirects_files \
        = process_options()

    logging_init(log_debug, log_filename)
    log.debug('Start %s version %s\nRun command:\n%s %s',
              PROGRAM_NAME, __version__, sys.executable, ' '.join(sys.argv))

    # setup field delimiter
    RedirectServer.field_delimiter = field_delimiter  # set once

    # process the passed redirects
    global Redirect_FromTo_List
    Redirect_FromTo_List = from_to  # set once
    global Redirect_Files_List
    redirects_files_ = [pathlib.Path(x) for x in redirects_files]
    Redirect_Files_List = redirects_files_  # set once
    # load the redirect entries from various sources
    entry_list = load_redirects(Redirect_FromTo_List,
                                Redirect_Files_List,
                                field_delimiter)
    global reload_datetime
    # distracting to read microsecond, set to 0
    reload_datetime = datetime.datetime.now().replace(microsecond=0)

    if len(entry_list) < 1:
        log.warning('There are no redirect entries')

    global status_path
    status_path = status_path_
    log.debug('status_path %s', status_path)

    global reload_path
    reload_path = reload_path_
    log.debug('reload_path %s', reload_path)

    redirect_code = http.HTTPStatus(int(redirect_code_))
    global Redirect_Code
    Redirect_Code = redirect_code
    log.debug('Successful Redirect Status Code is %s (%s)', int(redirect_code),
              redirect_code.phrase)

    # register the signal handler function
    log.debug('Register handler for signal %d (%s)',
              SIGNAL_RELOAD, SIGNAL_RELOAD)
    signal.signal(SIGNAL_RELOAD, reload_signal_handler)

    do_shutdown = False  # flag between threads MainThread and shutdown_thread

    def shutdown_server(redirect_server_: RedirectServer, shutdown_: int):
        log.debug('Server will shutdown in %s seconds', shutdown_)
        start = time.time()
        while time.time() - start < shutdown_:
            if do_shutdown:
                time.sleep(0.1)  # allow main thread time to print stacktrace
                break
            time.sleep(0.5)
        log.info("Calling shutdown on Redirect_Server %s (0x%08x)",
                 str(redirect_server_), id(redirect_server_))
        redirect_server_.shutdown()

    # create the first instance of the Redirect Handler
    redirect_handler = redirect_handler_factory(entry_list, redirect_code,
                                                status_path_, reload_path_)
    with RedirectServer((ip, port), redirect_handler) as redirect_server:
        serve_time = 'forever'
        if shutdown:
            serve_time = 'for %s seconds' % shutdown
            st = threading.Thread(
                name='shutdown_thread',
                target=shutdown_server,
                args=(redirect_server, shutdown,))
            st.start()
        log.info("Serve %s at %s:%s, Process ID %s", serve_time, ip, port,
                 os.getpid())
        try:
            log.debug("Redirect_Server %s (0x%08x)",
                      redirect_server, id(redirect_server))
            redirect_server.serve_forever(poll_interval=1)  # never returns
        except (KeyboardInterrupt, InterruptedError):
            do_shutdown = True
            raise


if __name__ == '__main__':
    main()
