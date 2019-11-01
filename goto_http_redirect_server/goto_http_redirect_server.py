#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# -*- pyversion: >=3.5.2 -*-
# TODO: BUG: status page reveals reload path and command line args.


import sys
import os
import typing
import argparse
import getpass
import datetime
import time
import signal
import threading
import socket
import socketserver
import uuid
import http
from http import server
import html
import csv
import pathlib
import copy
import json
import pprint
import logging
from urllib import parse
from collections import defaultdict


# canonical module informations used by setup.py
__version__ = '0.4.1'
__author__ = 'jtmoon79'
__url__ = 'https://github.com/jtmoon79/goto_http_redirect_server'
__url_issues__ = 'https://github.com/jtmoon79/goto_http_redirect_server/issues'
# first line of __doc__ is used in setup.py. Should match README.md and title at
# github.com project site.
__doc__ = """\
The "Go To" HTTP Redirect Server for sharing custom shortened HTTP URLs on your network.

Modules used are available within the standard CPython distribution.
Written for Python 3.7 but hacked to run with at least Python 3.5.
"""

#
# globals and constants initialization
#

PROGRAM_NAME = 'goto_http_redirect_server'
IP_LOCALHOST = '127.0.0.1'
HOSTNAME = socket.gethostname()

# HTTP Status Code used for redirects (among several possible redirect codes)
REDIRECT_CODE_DEFAULT = http.HTTPStatus.PERMANENT_REDIRECT
Redirect_Code = REDIRECT_CODE_DEFAULT

SIGNAL_RELOAD_UNIX = 'SIGUSR1'
SIGNAL_RELOAD_WINDOWS = 'SIGBREAK'
# signal to cause --redirects file reload
try:
    SIGNAL_RELOAD = signal.SIGUSR1  # Unix (not defined on Windows)
except AttributeError:
    SIGNAL_RELOAD = signal.SIGBREAK  # Windows (not defined on some Unix)

# ready logging module initializations (call logging_init to complete)
LOGGING_FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S'
LOGGING_FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'
# importers can override 'log'
log = logging.getLogger(PROGRAM_NAME)
# write-once copy of sys.argv
sys_args = []  # type: typing.List[str]

#
# Redirect Entry types
#
Re_From = typing.NewType('Re_From', str)  # Redirect From URI Path
Re_To = typing.NewType('Re_To', str)  # Redirect To URL Location
Re_User = typing.NewType('Re_User', str)  # User that created the Redirect (records-keeping thing, does not affect behavior)
Re_Date = typing.NewType('Re_Date', datetime.datetime)  # Datetime Redirect was created (records-keeping thing, does not affect behavior)
Re_EntryKey = typing.NewType('Re_EntryKey', Re_From)
Re_EntryValue = typing.NewType('Re_EntryValue',
                                typing.Tuple[Re_To, Re_User, Re_Date])
Re_Entry_Dict = typing.NewType('Re_Entry_Dict',
                               typing.Dict[Re_EntryKey, Re_EntryValue])
#
# other helpful types
#
Path_List = typing.List[pathlib.Path]
FromTo_List = typing.List[typing.Tuple[str, str]]
Redirect_Counter = typing.DefaultDict[str, int]
str_None = typing.Union[str, None]
Path_None = typing.Union[pathlib.Path, None]
#
# volatile global instances
#
# global list of --from-to passed redirects
Redirect_FromTo_List = []  # type: FromTo_List
# global list of --redirects files
Redirect_Files_List = []  # type: Path_List
reload = False
reload_datetime = None
redirect_counter = defaultdict(int)  # type: typing.DefaultDict[str, int]
status_path = None
reload_path = None
program_start_time = time.time()
STATUS_PAGE_PATH_DEFAULT = '/status'
FIELD_DELMITER_DEFAULT = '\t'
PATH_FAVICON = '/favicon.ico'
REDIRECT_PATHS_NOT_ALLOWED = (PATH_FAVICON,)

#
# functions, classes, code
#


class str_delay(object):
    """
    Delayed evaluation of object.__str__.
    Intended for logging messages that may not need to execute a passed function
    because the logging level may not be set.
    e.g.
       logging.debug('%s', complex_function(foo))
    The call to complex_function(foo) may not be necessary because logging.level
    might be logging.INFO. So skip the call to complex_function(foo) if it is
    not necessary, e.g.
       logging.debug('%s', str_delay(complex_function, foo))

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


def html_a(s_: str) -> str:
    """create HTML <a> from s_"""
    return '<a href="' + s_ + '">' + s_ + '</a>'


def combine_parseresult(pr1: parse.ParseResult, pr2: parse.ParseResult) -> str:
    """
    Combine parse.ParseResult parts.
    A parse.ParseResults example is
       parse.urlparse('http://host.com/path1;parmA=a,parmB=b?a=A&b=%20B&cc=CCC#FRAG')
    returns
        ParseResult(scheme='http', netloc='host.com', path='/path1',
                    params='parm2', query='a=A&b=%20B&cc=CCC', fragment='FRAG')

    pr1 is assumed to represent a Re_To supplied at startup-time
    pr2 is assumed to be an incoming request

    From pr1 use .scheme, .netloc, .path

    Combine .params, .query

    .query is combined such that a shorter redirect may be typed.
    For example, given RedirectEntry
       /b	http://bugzilla.corp.local/bug.cgi?id=	bob	
    User can GET URL (assuming running at host 'goto')
       'http://goto/b?123
    Which will become URL
       'http://bugzilla.corp.local/bug.cgi?id=123'

    From pr2 use .fragment

    Return a URL suitable for HTTP Header 'To'.
    """
    pr = pr1._asdict()
    pr['fragment'] = pr2.fragment
    if pr2.params:
        if pr1.params:
            # XXX: how are URI Object Parameters combined?
            #      see https://tools.ietf.org/html/rfc1808.html#section-2.1
            pr['params'] = pr1.params + ';' + pr2.params
        else:
            pr['params'] = pr2.params
    if pr2.query:
        if pr1.query:
            if pr1.query.endswith('='):
                pr['query'] = pr1.query + pr2.query
            else:
                pr['query'] = pr1.query + '&' + pr2.query
        else:
            pr['query'] = pr2.query
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
    Helper for printing (preferrably to stderr) and checking logging.DEBUG.
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
        _fromisoformat = datetime.datetime.fromisoformat

    try:
        dt = _fromisoformat(dts)
    except ValueError:
        log.error('bad datetime input (%s), fallback to current datetime', dts)
        dt = datetime.datetime.now()
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
              str_delay(pprint.pformat, redirects, indent=2)
    )

    class RedirectHandler(server.SimpleHTTPRequestHandler):

        def log_message(self, format_, *args, **kwargs):
            """
            override the RedirectHandler.log_message so RedirectHanlder
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

        def do_GET_status(self, path_: str):
            """dump status information about this server instance"""

            self.log_message('%s requested, returning %s (%s)',
                             path_,
                             int(http.HTTPStatus.OK),
                             http.HTTPStatus.OK.phrase,
                             loglevel=logging.INFO)
            self.send_response(http.HTTPStatus.OK)
            self.send_header('Redirect-Server-Host', HOSTNAME)
            self.send_header('Redirect-Server-Version', __version__)
            he = html_escape  # abbreviate

            # create the html body
            esc_title = he(
                '%s status' % PROGRAM_NAME)
            start_datetime = datetime.datetime.\
                fromtimestamp(program_start_time).replace(microsecond=0)
            uptime = time.time() - program_start_time
            esc_overall = he(
                'Program %s version %s and Project Page (%s)\n'
                'Process ID %s listening on %s:%s on host %s\n'
                'Process start datetime %s (up time %s)\n'
                'Successful Redirect Status Code is %s (%s)'
                % (PROGRAM_NAME, __version__, __url__,
                   os.getpid(), self.server.server_address[0],
                   self.server.server_address[1], HOSTNAME,
                   start_datetime, datetime.timedelta(seconds=uptime),
                   int(status_code), status_code.phrase,)
            )
            esc_args = he(' '.join(sys_args))
            esc_reload_datetime = he(reload_datetime.isoformat())

            def obj_to_html(obj, sort_keys=False):
                """Convert an object to html"""
                return he(
                    json.dumps(obj, indent=2, ensure_ascii=False,
                               sort_keys=sort_keys, default=str)
                    # pprint.pformat(obj)
                )

            def redirects_to_html(rd: Re_Entry_Dict):
                """Convert Re_Entry_Dict linkable html"""
                s_ = he('{\n')
                for key in sorted(rd.keys()):
                    val = rd[key]
                    s_ += he('  "') + html_a(key) + he('": [\n')
                    s_ += he('    "') + html_a(val[0]) + he('",\n')
                    s_ += he('    "%s",\n' % val[1])
                    s_ += he('    "%s"\n' % val[2])
                    s_ += he('  ]\n')
                s_ += he('\n}')
                return s_

            esc_reload_info =\
                '(process signal %d (%s)' % (SIGNAL_RELOAD, SIGNAL_RELOAD) \
                + (' or path "%s")' % reload_path_ if reload_path_ else ')')
            esc_reload_info = he(esc_reload_info)
            esc_redirects_counter = obj_to_html(redirect_counter)
            esc_redirects = redirects_to_html(redirects)
            esc_files = obj_to_html(Redirect_Files_List)
            html_doc = """\
<!DOCTYPE html>

<html lang="en">
  <head>
  <meta charset="utf-8"/>
  <title>{0}</title>
  </head>
  <body>
    <div>
        <h3>Process Information:</h3>
        <pre>
{1}
        </pre>
    </div>
    <div>
        <h4>Command-line Arguments:</h4>
        <pre>
{2}
        </pre>
    </div>
    <div>
        <h3>Redirects Counter:</h3>
        Counting of successful redirect responses:
        <pre>
{3}
        </pre>
        <h3>Currently Loaded Redirects:</h3>
        Last Reload Time {4}
        <pre>
{5}
        </pre>
    </div>
    <div>
        <h3>Redirect Files Searched During an Reload{6}:</h3>
        <pre>
{7}
        </pre>
    </div>
  </body>
</html>
"""\
                .format(esc_title,
                        esc_overall, esc_args,
                        esc_redirects_counter, esc_reload_datetime,
                        esc_redirects,
                        esc_reload_info,
                        esc_files)
            html_doc = bytes(html_doc, encoding='utf-8',
                             errors='xmlcharrefreplace')
            self.send_header('Content-Length', len(html_doc))
            self.end_headers()
            self.wfile.write(html_doc)

        def do_GET_reload(self, path_: str):
            # XXX: Could this be a security or stability risk?
            self.log_message('%s reload requested, returning %s (%s)',
                             path_,
                             int(http.HTTPStatus.NO_CONTENT),
                             http.HTTPStatus.NO_CONTENT.phrase,
                             loglevel=logging.INFO)
            self.send_response(http.HTTPStatus.NO_CONTENT)
            self.send_header('Redirect-Server-Host', HOSTNAME)
            self.send_header('Redirect-Server-Version', __version__)
            self.end_headers()
            global reload
            reload = True

        def do_GET_redirect(self,
                            parseresult: parse.ParseResult,
                            redirects_: Re_Entry_Dict):

            if parseresult.path not in redirects_.keys():
                self.log_message('no redirect found for (%s), returning %s (%s)',
                                 parseresult.path, int(http.HTTPStatus.NOT_FOUND),
                                 http.HTTPStatus.NOT_FOUND.phrase,
                                 loglevel=logging.INFO)
                self.send_response(http.HTTPStatus.NOT_FOUND)
                self.send_header('Redirect-Server-Host', HOSTNAME)
                self.send_header('Redirect-Server-Version', __version__)
                self.end_headers()
                return

            key = Re_EntryKey(Re_From(parseresult.path))
            parseresult_to = parse.urlparse(redirects_[key][0])
            user = redirects_[key][1]
            dt = redirects_[key][2]
            # merge RedirectEntry URI parts with incoming requested URI parts
            to = combine_parseresult(parseresult_to, parseresult)

            self.log_message('redirect found (%s) → (%s), returning %s (%s)',
                             key, to,
                             int(status_code), status_code.phrase,
                             loglevel=logging.INFO)

            self.send_response(status_code)
            # The 'Location' Header is used by browsers for HTTP 30X Redirects
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Location
            self.send_header('Redirect-Server-Host', HOSTNAME)
            self.send_header('Redirect-Server-Version', __version__)
            # the most important statement in this program
            self.send_header('Location', to)
            try:
                self.send_header('Redirect-Created-By', user)
            except UnicodeEncodeError:
                log.exception('header "Redirect-Created-By" set to fallback')
                self.send_header('Redirect-Created-By', 'Error Encoding User')
            self.send_header('Redirect-Created-Date', dt.isoformat())
            self.end_headers()
            count_key = '(%s) → (%s)' % (parseresult.path, to)
            redirect_counter[count_key] += 1
            return

        def do_GET(self) -> None:
            """invoked per HTTP GET Request"""
            print_debug('')
            try:
                self.log_message(
                    'self: %s\nself.client_address: %s\n'
                    'self.command: %s\nself.path: "%s"\n'
                    'self.headers:\n  %s',
                    self, self.client_address,
                    self.command, self.path,
                    str(self.headers).strip('\n').replace('\n', '\n  '),
                )
            except:
                log.exception('Failed to log GET request')

            parseresult = parse.urlparse(self.path)
            if parseresult.path == status_path_:
                self.do_GET_status(parseresult.path)
                return
            elif parseresult.path == reload_path_:
                self.do_GET_reload(parseresult.path)
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
                         field_delimiter: str) \
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
                        if not row:  # quietly skip empty rows
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
        re_key = Re_EntryKey(path)
        if re_key in entrys_files.keys():
            log.warning('Removing reserved From value "%s" from redirect entries.',
                        path)
            entrys_files.pop(path)

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
            log.warning('Removing To "Location" value "%s"; it fails encoding to "latin-1"',
                        to)
            remove.append(re_key)
    for re_key in remove:
        entrys_files.pop(re_key)

    return entrys_files


def load_redirects(from_to: FromTo_List,
                   redirects_files: Path_List,
                   field_delimiter: str) \
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


class RedirectServer(socketserver.TCPServer):
    """
    Custom Server to allow reloading redirects while serve_forever.
    """
    field_delimiter = FIELD_DELMITER_DEFAULT

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

        print_debug('.', end='')
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
        reload_datetime = datetime.datetime.now().replace(microsecond=0)  # distracting to read microsecond  
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
                                      pathlib.Path,
                                      str,
                                      str,
                                      int,
                                      int,
                                      str,
                                      FromTo_List,
                                      typing.List[str]]:
    """Process script command-line options."""

    rcd = REDIRECT_CODE_DEFAULT  # abbreviate
    global sys_args
    sys_args = copy.copy(sys.argv)  # set once

    parser = argparse.ArgumentParser(
        description="""\
The "Go To" HTTP Redirect Server! For sharing custom shortened HTTP URLs on your
network.

HTTP %s %s reply server. Load this server with redirects of "from path" and
"to URL" and let it run indefinitely. Reload the running server by
signaling the process.
"""
                    % (int(rcd), rcd.phrase),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog=PROGRAM_NAME,
        add_help=False
    )
    pgroup = parser.add_argument_group(title='Redirects',
                                       description='One or more required.'
                                       ' May be passed multiple times.')
    pgroup.add_argument('--from-to',
                        nargs=2, metavar=('from', 'to'),
                        action='append',
                        help='A single redirection of "from path" and'
                             ' "to URL" fields. For example,'
                             ' --from-to "/hr" "http://human-resources.mycorp.local/login"',
                        default=list())
    pgroup.add_argument('--redirects', dest='redirects_files', action='append',
                        help='File of redirection information. Within a file,'
                        ' is one redirection entry per line. An entry is four'
                        ' fields using tab character for field separator. The'
                        ' four entry fields are:'
                        ' "from path", "to URL", "added by user", and'
                        ' "added on datetime"'
                        ' separated by a tab.',
                        default=list())

    pgroup = parser.add_argument_group(title='Network Options')
    pgroup.add_argument('--ip', '-i', action='store', default=IP_LOCALHOST,
                        help='IP interface to listen on.'
                             ' Default is %(default)s .')
    pgroup.add_argument('--port', '-p', action='store', type=int, default=80,
                        help='IP port to listen on.'
                             ' Default is %(default)s .')

    pgroup = parser.add_argument_group(title='Miscellaneous Options')
    pgroup.add_argument('--status-path', action='store',
                        default=STATUS_PAGE_PATH_DEFAULT, type=str,
                        help='Override status page path. This is the page that'
                             ' dumps information about the process and loaded'
                             ' redirects.'
                             ' This can be the default landing page'
                             ' e.g. --status-path "/" .'
                             ' Default status page path is "%(default)s".')
    pgroup.add_argument('--reload-path', action='store',
                        default=None, type=str,
                        help='Allow reloads by HTTP GET Request to passed URI'
                             ' Path. e.g. --reload-path "/reload".'
                             ' May be a potential security or stability issue.'
                             ' The program will always allow reload by'
                             ' process signal.'
                             ' Default is off.')
    rc_302 = http.HTTPStatus.TEMPORARY_REDIRECT
    pgroup.add_argument('--redirect-code', action='store',
                        default=int(rcd), type=int,
                        help='Override default HTTP Redirect Status Code as an'
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
                        default=FIELD_DELMITER_DEFAULT,
                        help='Field delimiter string for --redirects files.'
                             ' Default is "%(default)s" (tab character)'
                             ' between fields.')
    pgroup.add_argument('--shutdown', action='store', type=int,
                        default=0,
                        help='Shutdown the server after passed seconds.'
                             ' Intended for testing.')
    pgroup.add_argument('--log', action='store', type=str, default=None,
                        help='Log to file at path LOG.'
                             ' Default logging is to sys.stderr.')
    pgroup.add_argument('--debug', action='store_true', default=False,
                        help='Set logging level to DEBUG.'
                             ' Default is INFO.')
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

  A redirects file entry has four fields separated by a tab character "\\t";
  "from path", "to URL", "added by user", "added on datetime".  For example,

    hr	http://human-resources.mycorp.local/login	bob	2019-09-07 12:00:00

  The last two fields, "added by user" and "added on datetime", are intended
  for record-keeping within an organization.

  A passed redirect (either via --from-to or --redirects file) should have a
  leading "/" as this is the URI path given for processing.
  For example, the URL "http://host/hr" is processed by {0}
  as URI path "/hr".

About Paths:

  Options --status-path and --reload-path may be passed paths to obscure access
  from unauthorized users. e.g.

      --status-path '/{1}'

About Reloads:

  Sending a process signal to the running process will cause
  a reload of any files passed via --redirects.  This allows live updating of
  redirect information without disrupting the running server process.
  On Unix, the signal is {2}.  On Windows, the signal is {3}.
  On this system, the signal is {4} ({5:d}).
  On Unix, use program `kill`.  On Windows, use program `windows-kill.exe`.

  A reload of redirection files may also be requested via passed URI path
  --reload-path '/path'.

  If security and stability are a concern then only allow reloads via process
  signals.

""".format(
        PROGRAM_NAME,
        str(uuid.uuid4()),
        SIGNAL_RELOAD_UNIX, SIGNAL_RELOAD_WINDOWS,
        str(SIGNAL_RELOAD), int(SIGNAL_RELOAD),
       )

    args = parser.parse_args()

    if not (args.from_to or args.redirects_files):
        print('ERROR: No redirect information was passed (--from-to or --redirects)',
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

    return \
        str(args.ip), \
        int(args.port), \
        args.debug, \
        log_filename, \
        args.status_path, \
        args.reload_path, \
        args.redirect_code, \
        args.shutdown,\
        args.field_delimiter, \
        args.from_to, \
        args.redirects_files


def main() -> None:
    ip, \
        port, \
        log_debug, \
        log_filename, \
        status_path_, \
        reload_path_, \
        redirect_code, \
        shutdown, \
        field_delimiter_, \
        from_to, \
        redirects_files \
        = process_options()

    logging_init(log_debug, log_filename)
    log.debug('Start %s version %s\nRun command:\n%s %s',
              PROGRAM_NAME, __version__, sys.executable, ' '.join(sys.argv))

    # setup field delimiter
    RedirectServer.field_delimiter = field_delimiter_  # set once

    # process the passed redirects
    global Redirect_FromTo_List
    Redirect_FromTo_List = from_to  # set once
    global Redirect_Files_List
    redirects_files_ = [pathlib.Path(x) for x in redirects_files]
    Redirect_Files_List = redirects_files_  # set once
    # load the redirect entries from various sources
    entry_list = load_redirects(Redirect_FromTo_List,
                                Redirect_Files_List,
                                field_delimiter_)
    global reload_datetime
    reload_datetime = datetime.datetime.now().replace(microsecond=0)  # distracting to read microsecond

    if len(entry_list) < 1:
        log.warning('There are no redirect entries')

    global status_path
    status_path = status_path_
    log.debug('status_path %s', status_path)

    global reload_path
    reload_path = reload_path_
    log.debug('reload_path %s', reload_path)

    redirect_code = http.HTTPStatus(redirect_code)
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
