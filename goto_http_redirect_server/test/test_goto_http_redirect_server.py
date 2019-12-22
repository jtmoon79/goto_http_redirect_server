#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
#
# This is easiest to run with helper script ./tools/pytest.sh


__author__ = 'jtmoon79'
__doc__ = \
    """Test the goto_http_redirect_server project using pytest."""

from collections import defaultdict
from datetime import datetime
import getpass
import http
from http import client
import threading
import time
import typing
from urllib.parse import ParseResult

import pytest

import goto_http_redirect_server
from goto_http_redirect_server.goto_http_redirect_server import (
    Re_Entry_Dict,
    Re_EntryKey,
    Re_EntryValue,
    Re_User,
    Re_Date,
    FromTo_List,
    REDIRECT_CODE_DEFAULT,
    query_match,
    query_match_contains,
    html_escape,
    html_a,
    htmls,
    combine_parseresult,
    print_debug,
    fromisoformat,
    load_redirects_fromto,
    redirect_handler_factory,
    RedirectHandler,
    RedirectServer,
)
str_None = typing.Optional[str]

# override for comparisons of datetime.now() generated values
NOW = datetime.now().replace(microsecond=0)
goto_http_redirect_server.goto_http_redirect_server.DATETIME_START = NOW
goto_http_redirect_server.goto_http_redirect_server.datetime_now = lambda: NOW

USER = getpass.getuser()

# all committed test resources should be under this directory
#resources = Path.joinpath(Path(__file__).parent, 'test_resources')


def pr(**kwargs):
    """create a ParseResult, sets unset parameters to empty string"""
    args = defaultdict(str, kwargs)
    return ParseResult(
        scheme=args['scheme'],
        netloc=args['netloc'],
        path=args['path'],
        params=args['params'],
        query=args['query'],
        fragment=args['fragment'],
    )

#def datetime_compare_nows(dts1, dts2):
#    """
#    compare two datetime.now() that were created during this test session
#    Does not handle midnight rollover of year/month/day! Good enough!!!
#    """
#    return dts1.year == dts2.year and \
#           dts1.month == dts2.month and \
#           dts1.day == dts2.day


class Test_Functions(object):

    @pytest.mark.parametrize(
        's_, expected',
        (
            pytest.param('', htmls(''),),
            pytest.param('A', htmls('A'),),
            pytest.param('&', htmls('&amp;'),),
            pytest.param('<>', htmls('&lt;&gt;'),),
            pytest.param('foo\nbar', htmls('foo<br />\nbar'),),
        )
    )
    def test_html_escape(self, s_: str, expected: htmls):
        actual = html_escape(s_)
        assert expected == actual
        assert type(expected) == type(actual)

    @pytest.mark.parametrize(
        'href, text, expected',
        (
            pytest.param('', None, '<a href=""></a>'),
            pytest.param('', '', '<a href=""></a>'),
            pytest.param('ABC', None, '<a href="ABC">ABC</a>'),
            pytest.param('ABC', '', '<a href="ABC"></a>'),
            pytest.param('ABC', '123', '<a href="ABC">123</a>'),
            pytest.param('<>', '<>', '<a href="<>">&lt;&gt;</a>'),
        )
    )
    def test_html_a(self, href: str, text: str_None, expected: str):
        actual = html_a(href, text)
        assert expected == actual

    @pytest.mark.parametrize(
        'dts, expected',
        (
            # these two cases will differ from Python 3.5 and subsequent Python versions
            #pytest.param('2001-01-02 03 04 05', datetime(year=2001, month=1, day=2, hour=3, minute=4, second=5)),
            #pytest.param('2002/01/02 03:04:05', datetime(year=2002, month=1, day=2, hour=3, minute=4, second=5)),
            pytest.param('2003-01-02 03:04:05', datetime(year=2003, month=1, day=2, hour=3, minute=4, second=5)),
            pytest.param('2004-01-02T03:04:05', datetime(year=2004, month=1, day=2, hour=3, minute=4, second=5)),
            pytest.param('BAD STRING', NOW),
        )
    )
    def test_fromisoformat(self, dts: str, expected: datetime):
        actual = fromisoformat(dts)
        assert expected == actual

    @pytest.mark.parametrize(
        'pr1, pr2, expected',
        (
            pytest.param(pr(path='a'), pr(path='a'), True),
            pytest.param(pr(path='a'), pr(path='a', query='b'), True),
            pytest.param(pr(path='a'), pr(path='b'), False),
            pytest.param(pr(query='a'), pr(path='b', query='a'), False),
        )
    )
    def test_query_match(self,
                         pr1: ParseResult,
                         pr2: ParseResult,
                         expected: bool):
        assert query_match(pr1, pr2) is expected

    # TODO: add test_query_match_find
    @pytest.mark.parametrize(
        'pr1, redirects, expected',
        (
            pytest.param(pr(path='/a'), {'/a': ('/b', USER, NOW)}, True),
            pytest.param(pr(path='/a'), {'/b': ('/a', USER, NOW)}, False),
        )
    )
    def test_query_match_contains(
            self,
            pr1: ParseResult,
            redirects: Re_Entry_Dict,
            expected: bool
    ):
        assert query_match_contains(pr1, redirects) is expected

    @pytest.mark.parametrize(
        'pr1,'
        'pr2,'
        'expected',
        (
            # URI component parts
            # https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlparse
            #
            # empty test cases
            pytest.param(
                pr(),
                pr(),
                '',
                id='(empty)'
            ),
            pytest.param(
                pr(scheme='http'),
                pr(scheme='http'),
                'http://',
                id='scheme http'
            ),
            pytest.param(
                pr(scheme='https'),
                pr(scheme='http'),
                'https://',
                id='scheme pr2'
            ),
            pytest.param(
                pr(scheme='https', netloc='a', path='b', params='c', query='d', fragment='e'),
                pr(),
                'https://a/b;c?d#e',
                id='pr1 only'
            ),
            pytest.param(
                pr(),
                pr(scheme='https', netloc='a', path='b', params='c', query='d', fragment='e'),
                ';c?d#e',
                id='pr2 only'
            ),
            pytest.param(
                pr(),
                pr(scheme='https', netloc='a', path='b', params='c', query='d', fragment='e'),
                ';c?d#e',
                id='pr2 only'
            ),
            # precedence test cases
            pytest.param(
                pr(scheme='ftp', netloc='a1'),
                pr(scheme='ftp', netloc='a2'),
                'ftp://a1',
                id='pr1.netloc'
            ),
            pytest.param(
                pr(scheme='ftp', netloc='a1', path='b1'),
                pr(scheme='ftp', netloc='a2', path='b2'),
                'ftp://a1/b1',
                id='pr1.netloc pr1.path'
            ),
            pytest.param(
                pr(scheme='ftp', netloc='a1', query='d1'),
                pr(scheme='ftp', netloc='a2', query='d2'),
                'ftp://a1?d1&d2',
                id='pr1.netloc pr1&2.query'
            ),
            pytest.param(
                pr(scheme='ftp', netloc='a1', fragment='f1'),
                pr(scheme='ftp', fragment='f2'),
                'ftp://a1#f2',
                id='pr2.fragment'
            ),
            # Template Syntax basic test cases
            pytest.param(
                pr(netloc='a1', path='p1_${path}'),
                pr(path='p2'),
                '//a1/p1_p2',
                id='Template Syntax: pr1.path "p1_${path}"'
            ),
            pytest.param(
                pr(netloc='a1', path='p1_${params}'),
                pr(params='r2'),
                '//a1/p1_r2',
                id='Template Syntax: pr1.path "p1_${params}"'
            ),
            pytest.param(
                pr(netloc='a1', path='p1_${query}'),
                pr(query='q2'),
                '//a1/p1_q2',
                id='Template Syntax: pr1.path "p1_${query}"'
            ),
            pytest.param(
                pr(netloc='a1', path='p1_${fragment}'),
                pr(fragment='f2'),
                '//a1/p1_f2',
                id='Template Syntax: pr1.path "p1_${fragment}"'
            ),
            pytest.param(
                pr(netloc='a1', params='r1_${path}'),
                pr(path='p2'),
                '//a1/;r1_p2',
                id='Template Syntax: pr1.params "r1_${path}"'
            ),
            pytest.param(
                pr(netloc='a1', query='q1_${path}'),
                pr(path='p2'),
                '//a1?q1_p2',
                id='Template Syntax: pr1.query "q1_${path}"'
            ),
            pytest.param(
                pr(netloc='a1', fragment='f1_${path}'),
                pr(path='p2'),
                '//a1#f1_p2',
                id='Template Syntax: pr1.fragment "f1_${path}"'
            ),
            # Template Syntax complex test cases
            # consuming ${path}
            # TODO: more tests around multiple same Template Syntax replacements
            #       is the current behavior a sensible approach?
            pytest.param(
                pr(netloc='a1', query='q1_${path}', fragment='f1_${path}'),
                pr(path='p2'),
                '//a1?q1_p2#f1_path',
                id='Template Syntax: consume ${path}'
            ),
        )
    )
    def test_combine_parseresult(self,
                                 pr1: ParseResult,
                                 pr2: ParseResult,
                                 expected: str):
        actual = combine_parseresult(pr1, pr2)
        assert expected == actual

    @pytest.mark.parametrize(
        'mesg, end',
        (
            pytest.param('', None),
            pytest.param('', ''),
            pytest.param('A', None),
            pytest.param('B', ''),
            pytest.param('C', '\n'),
        )
    )
    def test_print_debug(self, mesg: str, end: str):
        print_debug(mesg, end=end)

    @pytest.mark.parametrize(
        'href, text, expected',
        (
                pytest.param('', None, '<a href=""></a>'),
                pytest.param('', '', '<a href=""></a>'),
                pytest.param('ABC', None, '<a href="ABC">ABC</a>'),
                pytest.param('ABC', '', '<a href="ABC"></a>'),
                pytest.param('ABC', '123', '<a href="ABC">123</a>'),
                pytest.param('<>', '<>', '<a href="<>">&lt;&gt;</a>'),
        )
    )
    def test_html_a(self, href, text, expected):
        actual = html_a(href, text)
        assert expected == actual

    @pytest.mark.parametrize(
        'from_to, expected',
        (
            pytest.param(
                [
                    ('a', 'b',)
                ],
                Re_Entry_Dict({
                    'a': ('b', USER, NOW),
                }),
            ),
        )
    )
    def test_load_redirects_fromto(self, from_to: FromTo_List, expected: Re_Entry_Dict):
        actual = load_redirects_fromto(from_to)
        assert expected == actual


IP = '127.0.0.3'
PORT = 42395
ENTRY_LIST = {'/a': ('b', USER, NOW)}


def new_redirect_handler(redirects: Re_Entry_Dict) \
        -> RedirectHandler:
    return redirect_handler_factory(
        redirects,
        REDIRECT_CODE_DEFAULT,
        '/status',
        '/reload',
        htmls('')
    )


# thread target
def shutdown_server_thread(redirect_server: RedirectServer, sleep: int = 4):
    def shutdown_do(redirect_server_, sleep_):
        time.sleep(sleep_)
        redirect_server_.shutdown()

    st = threading.Thread(
        name='pytest-shutdown_thread',
        target=shutdown_do,
        args=(redirect_server, sleep))
    st.start()
    return st


# XXX: crude way to pass object from a thread back to main thread
global Request_Thread_Return
Request_Thread_Return = None
# XXX: crude thread synchronization!
global Request_Thread_Synch
Request_Thread_Synch = 0.5

# thread target
req_count = 0
def request_thread(ip: str, url: str, method: str):
    """caller should `.join` on thread"""
    def request_do(ip_: str, url_: str, method_: str):
        time.sleep(Request_Thread_Synch)
        cl = client.HTTPConnection(ip_, port=PORT, timeout=1)
        cl.request(method_, url_)
        global Request_Thread_Return
        Request_Thread_Return = cl.getresponse()

    global req_count
    req_count += 1
    rt = threading.Thread(
        name='pytest-request_thread-%d' % req_count,
        target=request_do,
        args=(ip, url, method,))
    rt.start()
    return rt


class Test_Classes(object):

    def test_RedirectServer_server_activate(self):
        with RedirectServer((IP, PORT), new_redirect_handler(ENTRY_LIST)) as redirect_server:
            redirect_server.server_activate()

    @pytest.mark.timeout(5)
    def test_RedirectServer_serve_forever(self):
        with RedirectServer((IP, PORT), new_redirect_handler(ENTRY_LIST)) as redirect_server:
            _ = shutdown_server_thread(redirect_server, 2)
            redirect_server.serve_forever(poll_interval=0.5)  # blocks


class Test_LiveServer(object):

    F302 = int(http.HTTPStatus.FOUND)  # 302
    NF404 = int(http.HTTPStatus.NOT_FOUND)  # 404
    R308 = int(REDIRECT_CODE_DEFAULT)  # 308
    ERR501 = int(http.HTTPStatus.NOT_IMPLEMENTED)  # 501

    URL = 'http://' + IP

    rd = {'/a': ('A', USER, NOW)}

    @pytest.mark.parametrize(
        'ip, url, loe, hi, method, redirects',
        (
            #
            # broad checks
            #
            pytest.param(IP, URL, 200, 499, 'GET', {}, id='broad check GET empty'),
            pytest.param(IP, URL, 200, 499, 'HEAD', {}, id='broad check HEAD empty'),
            pytest.param(IP, URL + '/X', 200, 499, 'GET', rd, id='broad check /X GET'),
            pytest.param(IP, URL + '/X', 200, 499, 'HEAD', rd, id='broad check /X HEAD'),
            #
            # precise checks - typical use-cases
            #
            pytest.param(IP, URL + '/X', NF404, None, 'GET', rd, id='GET Not Found'),
            pytest.param(IP, URL + '/X', NF404, None, 'HEAD', rd, id='HEAD Not Found'),
            # the two happy-path Redirect Found cases
            pytest.param(IP, URL + '/a', R308, None, 'GET', rd, id='GET Found'),
            pytest.param(IP, URL + '/a', R308, None, 'HEAD', rd, id='HEAD Found'),
            # make sure empty and None redirects is handled
            pytest.param(IP, URL + '/a', NF404, None, 'GET', {}, id='/a GET empty'),
            pytest.param(IP, URL + '/a', NF404, None, 'HEAD', {}, id='/a HEAD empty'),
            #
            # make sure other HTTP methods do nothing
            #
            pytest.param(IP, URL, ERR501, None, 'POST', {}, id='POST empty'),
            pytest.param(IP, URL, ERR501, None, 'PUT', {}, id='PUT empty'),
            pytest.param(IP, URL, ERR501, None, 'DELETE', {}, id='DELETE empty'),
            pytest.param(IP, URL, ERR501, None, 'OPTIONS', {}, id='OPTIONS empty'),
            pytest.param(IP, URL, ERR501, None, 'TRACE', {}, id='TRACE empty'),
            pytest.param(IP, URL, ERR501, None, 'PATCH', {}, id='PATCH empty'),
            pytest.param(IP, URL + '/a', ERR501, None, 'POST', rd, id='POST /a'),
            pytest.param(IP, URL + '/a', ERR501, None, 'PUT', rd, id='PUT /a'),
            pytest.param(IP, URL + '/a', ERR501, None, 'DELETE', rd, id='DELETE /a'),
            pytest.param(IP, URL + '/a', ERR501, None, 'OPTIONS', rd, id='OPTIONS /a'),
            pytest.param(IP, URL + '/a', ERR501, None, 'TRACE', rd, id='TRACE /a'),
            pytest.param(IP, URL + '/a', ERR501, None, 'PATCH', rd, id='PATCH /a'),
            pytest.param(IP, URL + '/', ERR501, None, 'POST', rd, id='POST /'),
            pytest.param(IP, URL + '/.', ERR501, None, 'POST', rd, id='POST /.'),
        )
    )
    @pytest.mark.timeout(10)
    def test_requests(self,
                      ip: str,
                      url: str,
                      loe: int,  # low bound or equal
                      hi: typing.Optional[int],  # high bound or None
                      method: str,
                      redirects: typing.Optional[Re_Entry_Dict]
                      ):
        with RedirectServer((ip, PORT), new_redirect_handler(redirects)) as redirect_server:
            global Request_Thread_Synch
            # XXX: crude synchronizations. Good enough for this test harness!
            srv_uptime = Request_Thread_Synch + 1
            thr_wait = Request_Thread_Synch + 0.3
            shutdown_server_thread(redirect_server, srv_uptime)
            rt = request_thread(ip, url, method)
            redirect_server.serve_forever(poll_interval=0.2)  # blocks for srv_uptime until server is shutdown
            rt.join(thr_wait)  # blocks for thr_wait until thread ends
            assert not rt.is_alive(), 'thread did not die in %s seconds' % thr_wait
            global Request_Thread_Return
            assert Request_Thread_Return is not None, 'the thread did not set the global Request_Thread_Return; unlucky time synch? did the thread crash?'
            if hi is None:
                assert loe == Request_Thread_Return.code
            else:
                assert loe <= Request_Thread_Return.code <= hi, "ip=(%s) url=(%s) method=(%s)" % (ip, url, method)
            Request_Thread_Return = None
