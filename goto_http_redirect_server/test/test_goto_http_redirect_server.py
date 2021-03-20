#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This is easiest to run with helper script ./tools/pytest.sh


__author__ = 'jtmoon79'
__doc__ = \
    """Test the goto_http_redirect_server project using pytest."""

from collections import defaultdict, OrderedDict
from datetime import datetime
import getpass
import http
from http import client
from pathlib import Path
from pprint import pformat
import sys
import threading
import time
import timeit
import typing
import urllib
from urllib.parse import ParseResult

import pytest

import goto_http_redirect_server
from goto_http_redirect_server.goto_http_redirect_server import (
    DATETIME_STRPTIMES,
    FIELD_DELIMITER_DEFAULT,
    Re_User,
    Re_Date,
    Re_Entry,
    Re_EntryType,
    Re_EntryKey,
    Re_Entry_Dict,
    Re_Entry_Dict_new,
    FromTo_List,
    Path_List,
    REDIRECT_PATHS_NOT_ALLOWED,
    REDIRECT_CODE_DEFAULT,
    html_escape,
    html_a,
    htmls,
    print_debug,
    dts_to_datetime,
    to_ParseResult,
    redirect_handler_factory,
    RedirectHandler,
    RedirectServer,
    RedirectsLoader,
)
str_None = typing.Optional[str]

# override for comparisons of datetime.now() generated values
NOW = datetime.now().replace(microsecond=0)
goto_http_redirect_server.goto_http_redirect_server.DATETIME_START = NOW
goto_http_redirect_server.goto_http_redirect_server.datetime_now = lambda: NOW
# need something different than NOW
LATER = datetime.now().replace(microsecond=0)
LATER = LATER.replace(second=(LATER.second + 1 if LATER.second < 59 else 0))
assert NOW != LATER

USER = goto_http_redirect_server.goto_http_redirect_server.USER_DEFAULT

# shorten some names for clarity
topr = to_ParseResult
ET = Re_EntryType


# all committed test resources should be under this directory
#resources = Path.joinpath(Path(__file__).parent, 'test_resources')


def pr(**kwargs) -> ParseResult:
    """helper to create a `ParseResult`, sets unset parameters to empty string"""
    args = defaultdict(str, kwargs)
    return ParseResult(
        scheme=args['scheme'],
        netloc=args['netloc'],
        path=args['path'],
        params=args['params'],
        query=args['query'],
        fragment=args['fragment'],
    )


def datetime_str(datetime_as_str: str) -> datetime:
    """
    Helper to create a `datetime` from a string in particular format
    """
    for strptime_format in DATETIME_STRPTIMES:
        try:
            return datetime.strptime(datetime_as_str, strptime_format)
        except:
            pass
    raise ValueError("Could not convert string '%s' to datetime" % (datetime_as_str,))


class Test_ClassesSimple(object):
    """basic building-block classes"""

    @pytest.mark.parametrize(
        'entry_args, entry_kwargs,'
        'entry_expected, raises',
        (
                # basic error case
                pytest.param((), {},
                             None, ValueError),
                # basic happy path
                pytest.param(('a', 'b'), {},
                             Re_Entry('a', 'b'), None),
                # different Re_EntryType
                pytest.param(('a', 'b'), {},
                             Re_Entry('a', 'b', USER, NOW, topr('a'), topr('b'), ET._), None),
                pytest.param(('a;', 'b'), {},
                             Re_Entry('a;', 'b', USER, NOW, topr('a;'), topr('b'), ET._P), None),
                pytest.param(('a;?', 'b'), {},
                             Re_Entry('a;?', 'b', USER, NOW, topr('a;?'), topr('b'), ET._PQ), None),
                pytest.param(('a?', 'b'), {},
                             Re_Entry('a?', 'b', USER, NOW, topr('a?'), topr('b'), ET._Q), None),
                # different args
                pytest.param(('a', 'b', 'u3'), {},
                             Re_Entry('a', 'b', 'u3', NOW, topr('a'), topr('b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER), {},
                             Re_Entry('a', 'b', 'u3', LATER, topr('a'), topr('b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER, topr('NOT a')), {},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b')), {},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), {},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), None),
                # different kwargs
                pytest.param(('a', 'b'), {'user': 'u3'},
                             Re_Entry('a', 'b', 'u3', NOW, topr('a'), topr('b'), ET._), None),
                pytest.param(('a', 'b', 'u3'), {'date': LATER},
                             Re_Entry('a', 'b', 'u3', LATER, topr('a'), topr('b'), ET._), None),
                pytest.param(('a', 'b'), {'user': 'u3', 'date': LATER},
                             Re_Entry('a', 'b', 'u3', LATER, topr('a'), topr('b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER), {'from_pr': topr('NOT a')},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('b'), ET._), None),
                pytest.param(('a', 'b', 'u3'), {'date': LATER, 'from_pr': topr('NOT a')},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('b'), ET._), None),
                pytest.param(('a', 'b'), {'user': 'u3', 'date': LATER, 'from_pr': topr('NOT a')},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER, topr('NOT a')), {'to_pr': topr('NOT b')},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER), {'from_pr': topr('NOT a'), 'to_pr': topr('NOT b')},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._), None),
                pytest.param(('a', 'b', 'u3'), {'date': LATER, 'from_pr': topr('NOT a'), 'to_pr': topr('NOT b')},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._), None),
                pytest.param(('a', 'b'), {'user': 'u3', 'date': LATER, 'from_pr': topr('NOT a'), 'to_pr' :topr('NOT b')},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._), None),
                pytest.param(('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b')), {'etype': ET._P},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), None),
                pytest.param(('a', 'b', 'u3', LATER, topr('NOT a')), {'to_pr': topr('NOT b'), 'etype': ET._P},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), None),
                pytest.param(('a', 'b', 'u3', LATER), {'from_pr': topr('NOT a'), 'to_pr': topr('NOT b'), 'etype': ET._P},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), None),
                pytest.param(('a', 'b', 'u3'), {'date': LATER, 'from_pr': topr('NOT a'), 'to_pr': topr('NOT b'), 'etype': ET._P},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), None),
                pytest.param(('a', 'b'), {'user': 'u3', 'date': LATER, 'from_pr': topr('NOT a'), 'to_pr': topr('NOT b'), 'etype': ET._P},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), None),
                # all kwargs
                pytest.param((), {'from_': 'a', 'to': 'b', 'user': 'u3', 'date': LATER, 'from_pr': topr('NOT a'), 'to_pr': topr('NOT b'), 'etype': ET._P},
                             Re_Entry('a', 'b', 'u3', LATER, topr('NOT a'), topr('NOT b'), ET._P), None),
        )
    )
    def test_Re_Entry(self,
                      entry_args,
                      entry_kwargs,
                      entry_expected,
                      raises):
        if raises:
            with pytest.raises(raises):
                Re_Entry(*entry_args, **entry_kwargs)
        else:
            entry = Re_Entry(*entry_args, **entry_kwargs)
            assert entry == entry_expected


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
        assert type(actual) == type(expected)

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
    def test_html_a(self,
                    href: str,
                    text: str_None,
                    expected: str):
        actual = html_a(href, text)
        assert actual == expected

    @pytest.mark.parametrize(
        'dts, expected',
        (
            pytest.param('2001-01-02 03:04:05', datetime(year=2001, month=1, day=2, hour=3, minute=4, second=5)),
            pytest.param('2002-01-02T03:04:05', datetime(year=2002, month=1, day=2, hour=3, minute=4, second=5)),
            pytest.param('2003-01-02_03:04:05', datetime(year=2003, month=1, day=2, hour=3, minute=4, second=5)),
            pytest.param('2004-01-02 03:04', datetime(year=2004, month=1, day=2, hour=3, minute=4)),
            pytest.param('2005-01-02_03:04', datetime(year=2005, month=1, day=2, hour=3, minute=4)),
            pytest.param('2006/01/02_03:04', datetime(year=2006, month=1, day=2, hour=3, minute=4)),
            pytest.param('2007-01-02', datetime(year=2007, month=1, day=2)),
            pytest.param('2008/01/02', datetime(year=2008, month=1, day=2)),
            pytest.param('BAD STRING', NOW),
        )
    )
    def test_dts_to_datetime(self,
                           dts: str,
                           expected: datetime):
        actual = dts_to_datetime(dts)
        assert  actual == expected

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
        assert RedirectHandler.query_match(pr1, pr2) is expected

    @pytest.mark.parametrize(
        'ppq, ppqpr,'
        'redirects,'
        'entry',
        (
            pytest.param(
                '/a0', pr(path='/a0'),
                {'/a0': Re_Entry('/a0', '/b')},
                Re_Entry('/a0', '/b')
            ),
            pytest.param(
                '/a1', pr(path='/a1'),
                {'/b': Re_Entry('/a1', '/b')},
                None,
            ),
            pytest.param(
                '/a2', pr(path='/a2'),
                {'/a2': Re_Entry('/a2', '/b'), '/a2;': Re_Entry('/a2;', '/b')},
                Re_Entry('/a2', '/b'),
            ),
            pytest.param(
                '/a3', pr(path='/a3'),
                {'/a3;': Re_Entry('/a3;', '/b'), '/a3;?': Re_Entry('/a3;?', '/b'), '/a3?': Re_Entry('/a3?', '/b'), '/a3': Re_Entry('/a3', '/b')},
                Re_Entry('/a3', '/b'),
            ),
            pytest.param(
                '/a4', pr(path='/a4'),
                {'/a4;': Re_Entry('/a4;', '/b'), '/a4?': Re_Entry('/a4?', '/b'), '/a4': Re_Entry('/a4', '/b'), '/a4;?': Re_Entry('/a4;?', '/b')},
                Re_Entry('/a4', '/b'),
            ),
            pytest.param(
                '/a5;c', pr(path='/a5', params='c'),
                {'/a5': Re_Entry('/a5', '/b'), '/a5;': Re_Entry('/a5;', '/b')},
                Re_Entry('/a5;', '/b'),
            ),
            pytest.param(
                '/a?00', pr(path='/a', query='00'),
                {'/a;': Re_Entry('/a;', '/b'), '/a;?': Re_Entry('/a;?', '/b')},
                None,
            ),
            pytest.param(
                '/a?01', pr(path='/a', query='01'),
                {'/a': Re_Entry('/a', '/b'), '/a;': Re_Entry('/a;', '/b')},
                Re_Entry('/a', '/b'),
            ),
            pytest.param(
                '/a;02', pr(path='/a', params='02'),
                {'/a': Re_Entry('/a', '/b'), '/a?': Re_Entry('/a?', '/b')},
                Re_Entry('/a', '/b'),
            ),
            pytest.param(
                '/a;03', pr(path='/a', params='03'),
                {'/a;?': Re_Entry('/a;?', '/b'), '/a?': Re_Entry('/a?', '/b')},
                None,
            ),
            pytest.param(
                '/a?04', pr(path='/a', query='04'),
                {'/a;': Re_Entry('/a;', '/b'), '/a?': Re_Entry('/a?', '/b')},
                Re_Entry('/a?', '/b'),
            ),
            pytest.param(
                '/a?05', pr(path='/a', query='05'),
                {'/a;': Re_Entry('/a;', '/b'), '/a;?': Re_Entry('/a;?', '/b')},
                None,
            ),
            pytest.param(
                '/a?06', pr(path='/a', query='06'),
                {'/a;': Re_Entry('/a;', '/b'), '/a;?': Re_Entry('/a;?', '/b'), '/a?': Re_Entry('/a?', '/b')},
                Re_Entry('/a?', '/b'),
            ),
            pytest.param(
                '/a?07', pr(path='/a', query='07'),
                {'/a;': Re_Entry('/a;', '/b'), '/a;?': Re_Entry('/a;?', '/b'), '/a?': Re_Entry('/a?', '/b'), '/a': Re_Entry('/a', '/b')},
                Re_Entry('/a?', '/b'),
            ),
            # XXX: Disable Path Required Request Modifier
            # with paths
            # pytest.param(
            #     '/d/path?00', pr(path='/d/path', query='00'),
            #     {'/d;': Re_Entry('/d;', '/b'), '/d;?': Re_Entry('/d;?', '/b')},
            #     None,
            # ),
            # pytest.param(
            #     '/d/path?01', pr(path='/d/path', query='01'),
            #     {'/d': Re_Entry('/d', '/b'), '/d/?': Re_Entry('/d/?', '/b')},
            #     Re_Entry('/d/?', '/b'),
            # ),
            # pytest.param(
            #     '/d;02', pr(path='/d', params='02'),
            #     {'/d': Re_Entry('/d', '/b'), '/d?': Re_Entry('/d?', '/b')},
            #     Re_Entry('/d', '/b'),
            # ),
            # pytest.param(
            #     '/d;03', pr(path='/d', params='03'),
            #     {'/d;?': Re_Entry('/d;?', '/b'), '/d?': Re_Entry('/d?', '/b')},
            #     None,
            # ),
            # pytest.param(
            #     '/d?04', pr(path='/d', query='04'),
            #     {'/d;': Re_Entry('/d;', '/b'), '/d?': Re_Entry('/d?', '/b')},
            #     Re_Entry('/d?', '/b'),
            # ),
            # pytest.param(
            #     '/d?05', pr(path='/d', query='05'),
            #     {'/d;': Re_Entry('/d;', '/b'), '/d;?': Re_Entry('/d;?', '/b')},
            #     None,
            # ),
            # pytest.param(
            #     '/d?06', pr(path='/d', query='06'),
            #     {'/d;': Re_Entry('/d;', '/b'), '/d;?': Re_Entry('/d;?', '/b'), '/d?': Re_Entry('/d?', '/b')},
            #     Re_Entry('/d?', '/b'),
            # ),
            # pytest.param(
            #     '/d?07', pr(path='/d', query='07'),
            #     {'/d;': Re_Entry('/d;', '/b'), '/d;?': Re_Entry('/d;?', '/b'), '/d?': Re_Entry('/d?', '/b'), '/d': Re_Entry('/d', '/b')},
            #     Re_Entry('/d?', '/b'),
            # ),
        )
    )
    def test_query_match_finder(self,
                                ppq: str, ppqpr: ParseResult,
                                redirects: Re_Entry_Dict,
                                entry: Re_Entry):
        """
        Test `RedirectHandler.query_match_finder` returns explected `Re_Entry`
        """
        assert RedirectHandler.query_match_finder(
            ppq, ppqpr,
            redirects) == entry

    def test_ppq_cache_clear(self):
        """
        Simple test `RedirectHandler.ppq_cache_clear` runs and does not raise.
        """
        RedirectHandler.ppq_cache_clear()
        assert len(RedirectHandler._ppq_cache) == 0

    _test_ppq_cache_redirects = Re_Entry_Dict_new(
        [
            ('/a1', Re_Entry('/a1', '/A1')),
            ('/a2;', Re_Entry('/a2;', '/A2a')),
            ('/a2?', Re_Entry('/a2?', '/A2b')),
            ('/a3', Re_Entry('/a3', '/A3')),
        ]
    )

    @pytest.mark.parametrize(
        'ppq, ppqpr,'
        'redirects,'
        'entry, ppq_cache_len, ppq_cache_check',
        (
            # order is important, the state of RedirectHandler._ppq_cache
            # is carried forward after each test
            pytest.param(
                '/a1', pr(path='/a1'),
                _test_ppq_cache_redirects,
                Re_Entry('/a1', '/A1'), 1, False
            ),
            pytest.param(
                '/a2', pr(path='/a2'),
                _test_ppq_cache_redirects,
                Re_Entry('/a2;', '/A2a'), 2, False
            ),
            pytest.param(
                '/a2', pr(path='/a2'),
                _test_ppq_cache_redirects,
                Re_Entry('/a2;', '/A2a'), 2, True
            ),
            pytest.param(
                '/a2?foo', pr(path='/a2', query='foo'),
                _test_ppq_cache_redirects,
                Re_Entry('/a2?', '/A2b'), 2, False
            ),
            pytest.param(
                '/x', pr(path='/x'),
                _test_ppq_cache_redirects,
                None, 2, False
            ),
            pytest.param(
                '/a2', pr(path='/a2'),
                _test_ppq_cache_redirects,
                Re_Entry('/a2;', '/A2a'), 2, False
            ),
            pytest.param(
                '/a3', pr(path='/a3'),
                _test_ppq_cache_redirects,
                Re_Entry('/a3', '/A3'), 2, False
            ),
            pytest.param(
                '/a3', pr(path='/a3'),
                _test_ppq_cache_redirects,
                Re_Entry('/a3', '/A3'), 2, True
            ),
            pytest.param(
                '/a2', pr(path='/a2'),
                _test_ppq_cache_redirects,
                Re_Entry('/a2;', '/A2a'), 2, False
            ),
        )
    )
    def test_ppq_cache(
        self,
        ppq: str,
        ppqpr: ParseResult,
        redirects: Re_Entry_Dict,
        entry: Re_Entry,
        ppq_cache_len: int,
        ppq_cache_check: bool
    ):
        """
        Test `RedirectHandler` works.

        XXX: `RedirectHandler.test_ppq_cache_clear` must run once just before this
             this test case should be redesigned to not have that dependency,
             or use a pytest fixture that can wrap series of paremetrize tests
        """
        # XXX: sanity check
        assert RedirectHandler.ppq_cache_enabled
        RedirectHandler._ppq_cache_max = 2

        if ppq_cache_check:
            assert RedirectHandler._ppq_cache_check(ppq, redirects)
        else:
            assert RedirectHandler._ppq_cache_check(ppq, redirects) == (None, None)
        entry_, _ = RedirectHandler._do_VERB_redirect_processing(ppq, ppqpr, redirects)
        assert entry_ == entry
        assert len(RedirectHandler._ppq_cache) == ppq_cache_len

    @pytest.mark.parametrize(
        "ppq, ppqpr,"
        "redirects,"
        "ppq_cache_len, ppq_cache_enabled, ppq_cache_clear",
        (
            pytest.param(
                '/a1', pr(path='/a1'),
                _test_ppq_cache_redirects,
                0, False, True,
            ),
            pytest.param(
                '/a2', pr(path='/a2'),
                _test_ppq_cache_redirects,
                0, False, False,
            ),
            pytest.param(
                '/a2', pr(path='/a2'),
                _test_ppq_cache_redirects,
                1, True, False,
            ),
        )
    )
    def test_ppq_cache_enabled(
        self,
        ppq: str,
        ppqpr: ParseResult,
        redirects: Re_Entry_Dict,
        ppq_cache_len: int,
        ppq_cache_enabled: bool,
        ppq_cache_clear: bool,
    ):
        """
        Test `RedirectHandler.ppq_cache_enabled` flag enables or disables caching.
        """
        if ppq_cache_clear:
            RedirectHandler.ppq_cache_clear()
        RedirectHandler.ppq_cache_enabled = ppq_cache_enabled
        _, __ = RedirectHandler._do_VERB_redirect_processing(ppq, ppqpr, redirects)
        assert len(RedirectHandler._ppq_cache) == ppq_cache_len

    @pytest.mark.parametrize(
        "redirects_len, timeit_number, ppq_cache_max",
        (
            pytest.param(100, 100, 50),
            pytest.param(100, 1000, 50),
            pytest.param(1000, 100, 50),
            pytest.param(1000, 1000, 50),
            pytest.param(10000, 100, 50),
            pytest.param(10000, 1000, 50),
        ),
    )
    def test_ppq_cache_enabled_timeit(
        self,
        redirects_len: int,
        timeit_number: int,
        ppq_cache_max: int,
    ):
        """
        Test the `RedirectHandler._ppq_cache` is actually useful by timing the
        difference with and without via `ppq_cache_enabled` flag
        """
        time_start = time.time()
        RedirectHandler._ppq_cache_max = ppq_cache_max

        def _gen_redirects(redirects_len_: int) -> Re_Entry_Dict:
            """generate a `Re_Entry_Dict` of size `redirects_len_`."""
            redirects_ = Re_Entry_Dict_new()
            for i_ in range(0, redirects_len_):
                from_ = "/%08X" % i_
                to_ = "/%08X" % i_
                redirects_[Re_EntryKey(from_)] = Re_Entry(from_, to_)
            return redirects_

        # generate the redirects entries
        redirects = _gen_redirects(redirects_len)
        # create a small variety of lookups
        lookups = list()
        for l_ in (
            "/NO-MATCH1",
            #"/NO-MATCH2;f",
            #"/NO-MATCH3;f?a=A",
            #"/NO-MATCH4#foobar",
            # should match generated entries in `_gen_redirects`
            "/%08X" % 1,
            "/%08X?a=A" % 2,
            "/%08X#c" % 3,
            "/%08X?a=A&b=B#c" % 4,
            "/%08X?a=A&b=B#c" % int(redirects_len / 2),
            "/%08X?a=A&b=B#c" % (redirects_len - 2),
            "/%08X?a=A&b=B#c" % (redirects_len - 1),
        ):
            lookups.append((l_, urllib.parse.urlparse(l_),))

        # save `cache_enabled` setting
        cache_enabled_prev = RedirectHandler.ppq_cache_enabled

        print("", file=sys.stderr)
        results = {True: None, False: None}
        for cache_enabled in (True, False,):
            # set `cache_enabled` to test setting, clear cache
            RedirectHandler.ppq_cache_enabled = cache_enabled
            RedirectHandler.ppq_cache_clear()

            print("timeit(%4d) lookups len %d, redirects size %-5d, cache enabled %-5s: "
                  % (timeit_number, len(lookups), len(redirects),
                     RedirectHandler.ppq_cache_enabled,),
                  end="", file=sys.stderr)
            sys.stdout.flush()
            sys.stderr.flush()

            # timeit code
            def stmt_():
                for (ppq, ppqpr) in lookups:
                    __, ___ = RedirectHandler._do_VERB_redirect_processing(ppq, ppqpr, redirects)
            time1 = timeit.Timer(stmt=stmt_, globals=globals()).timeit(number=timeit_number)

            # print timeit results
            print("%1.6f" % (time1,), file=sys.stderr)
            sys.stdout.flush()
            sys.stderr.flush()
            # save timeit results for later assert
            results[cache_enabled] = time1
        # restore `cache_enabled` setting, clear cache
        RedirectHandler.ppq_cache_enabled = cache_enabled_prev
        RedirectHandler.ppq_cache_clear()
        time_stop = time.time()
        print("total time taken for test case %40s%1.6f" % ("", time_stop - time_start,), file=sys.stderr)
        # the cache disabled should be larger value (longer time; slower) than cache enabled
        assert results[False] > results[True]

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
                r'http://',
                id='scheme http'
            ),
            pytest.param(
                pr(scheme='https'),
                pr(scheme='http'),
                r'https://',
                id='scheme pr2'
            ),
            pytest.param(
                pr(scheme='https', netloc='a', path='b', params='c', query='d', fragment='e'),
                pr(),
                r'https://a/b;c?d#e',
                id='pr1 only'
            ),
            pytest.param(
                pr(),
                pr(scheme='https', netloc='a', path='b', params='c', query='d', fragment='e'),
                r';c?d#e',
                id='pr2 only'
            ),
            pytest.param(
                pr(),
                pr(scheme='https', netloc='a', path='b', params='c', query='d', fragment='e'),
                r';c?d#e',
                id='pr2 only'
            ),
            # precedence test cases
            pytest.param(
                pr(scheme='ftp', netloc='a1'),
                pr(scheme='ftp', netloc='a2'),
                r'ftp://a1',
                id='pr1.netloc'
            ),
            pytest.param(
                pr(scheme='ftp', netloc='a1', path='b1'),
                pr(scheme='ftp', netloc='a2', path='b2'),
                r'ftp://a1/b1',
                id='pr1.netloc pr1.path'
            ),
            pytest.param(
                pr(scheme='ftp', netloc='a1', query='d1'),
                pr(scheme='ftp', netloc='a2', query='d2'),
                r'ftp://a1?d1&d2',
                id='pr1.netloc pr1&2.query'
            ),
            pytest.param(
                pr(scheme='ftp', netloc='a1', fragment='f1'),
                pr(scheme='ftp', fragment='f2'),
                r'ftp://a1#f2',
                id='pr2.fragment'
            ),
            # Template Syntax basic test cases
            pytest.param(
                pr(netloc='a1', path='p1_${path}'),
                pr(path='p2'),
                r'//a1/p1_p2',
                id='Template Syntax: pr1.path "p1_${path}"'
            ),
            pytest.param(
                pr(netloc='a1', path='p1_${params}'),
                pr(params='r2'),
                r'//a1/p1_r2',
                id='Template Syntax: pr1.path "p1_${params}"'
            ),
            pytest.param(
                pr(netloc='a1', path='p1_${query}'),
                pr(query='q2'),
                r'//a1/p1_q2',
                id='Template Syntax: pr1.path "p1_${query}"'
            ),
            pytest.param(
                pr(netloc='a1', path='p1_${fragment}'),
                pr(fragment='f2'),
                r'//a1/p1_f2',
                id='Template Syntax: pr1.path "p1_${fragment}"'
            ),
            pytest.param(
                pr(netloc='a1', params='r1_${path}'),
                pr(path='p2'),
                r'//a1/;r1_p2',
                id='Template Syntax: pr1.params "r1_${path}"'
            ),
            pytest.param(
                pr(netloc='a1', query='q1_${path}'),
                pr(path='p2'),
                r'//a1?q1_p2',
                id='Template Syntax: pr1.query "q1_${path}"'
            ),
            pytest.param(
                pr(netloc='a1', fragment='f1_${path}'),
                pr(path='p2'),
                r'//a1#f1_p2',
                id='Template Syntax: pr1.fragment "f1_${path}"'
            ),
            # Template Syntax complex test cases
            # consuming ${path}
            # XXX: these are the odd behaviors of current implementation
            pytest.param(
                pr(netloc='a1', query='q1_${path}', fragment='f1_${path}'),
                pr(path='p2'),
                r'//a1?q1_p2#f1_path',
                id='Template Syntax1: consume ${path}'
            ),
            pytest.param(
                pr(netloc='a1_${path}', query='q1_${path}', fragment='f1'),
                pr(path='p2'),
                r'//a1_p2?q1_path#f1',
                id='Template Syntax2: consume ${path}'
            ),
            pytest.param(
                pr(netloc='a1', params='prm1', query='q1_${path}', fragment='f1'),
                pr(path='p2', params='prm2'),
                r'//a1/;prm1;prm2?q1_p2#f1',
                id='Template Syntax3: consume ${path}'
            ),
            pytest.param(
                pr(netloc='a1', query='q1_${query}', fragment='f1_${query}'),
                pr(path='p2'),
                r'//a1?q1_#f1_query',
                id='Template Syntax4: consume ${query}'
            ),
            pytest.param(
                pr(netloc='a1_${query}', query='q1_${query}', fragment='f1'),
                pr(path='p2'),
                r'//a1_?q1_query#f1',
                id='Template Syntax5: consume ${query}'
            ),
            pytest.param(
                pr(netloc='a1', params='prm1', query='q1_${query}', fragment='f1'),
                pr(path='p2', params='prm2', query='q2'),
                r'//a1/;prm1;prm2?q1_q2#f1',
                id='Template Syntax6: consume ${query}'
            ),
        )
    )
    def test_combine_parseresult(self,
                                 pr1: ParseResult,
                                 pr2: ParseResult,
                                 expected: str):
        actual = RedirectHandler.combine_parseresult(pr1, pr2)
        assert actual == expected

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
    def test_print_debug(self,
                         mesg: str,
                         end: str):
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
    def test_html_a(self,
                    href,
                    text,
                    expected):
        actual = html_a(href, text)
        assert actual == expected

    @pytest.mark.parametrize(
        'from_to, expected',
        (
            pytest.param(
                [('a', 'A')], Re_Entry_Dict_new([('a', Re_Entry('a', 'A'))])
            ),
            pytest.param(
                [('a', 'A'), ('b', 'B')],
                Re_Entry_Dict_new([('a', Re_Entry('a', 'A')), ('b', Re_Entry('b', 'B'))])
            ),
            pytest.param(
                [('a', 'A'), ('b', 'B'), ('b', 'X')],
                Re_Entry_Dict_new([('a', Re_Entry('a', 'A')), ('b', Re_Entry('b', 'B'))])
            )
        ),
    )
    def test_load_redirects_fromto(self,
                                   from_to: FromTo_List,
                                   expected: Re_Entry_Dict):
        actual = RedirectsLoader.load_redirects_fromto(from_to)
        assert actual == expected

    @pytest.mark.parametrize(
        'input_, expected',
        (
            # simply happy path
            pytest.param(
                {'a': Re_Entry('a', 'b')},
                {'a': Re_Entry('a', 'b')},
            ),
            # reserved path
            pytest.param(
                {REDIRECT_PATHS_NOT_ALLOWED[0]: Re_Entry(REDIRECT_PATHS_NOT_ALLOWED[0], 'b')},
                {},
            ),
            # encoding not allowed
            pytest.param(
                {'a': Re_Entry('a', r'混沌')},
                {},
            ),
            # encoding allowed in `to` field
            pytest.param(
                {r'混沌': Re_Entry(r'混沌', 'b')},
                {r'混沌': Re_Entry(r'混沌', 'b')},
            ),
        )
    )
    def test_clean_redirects(self,
                             input_: Re_Entry_Dict,
                             expected: Re_Entry_Dict):
        actual = RedirectsLoader.clean_redirects(input_)
        assert actual == expected

    @pytest.mark.parametrize(
        'redirects_files, expected',
        (
            pytest.param(
                [Path("./goto_http_redirect_server/test/re6.csv")],
                Re_Entry_Dict_new(
                    [
                        ("/r1", Re_Entry("/r1", "http://www.r1.com", "bob1",
                                         datetime_str("2020-01-01 00:00:00"))),
                        ("/r2", Re_Entry("/r2", "http://www.r2.com", "bob2",
                                         datetime_str("2020-01-02 00:00:00"))),
                    ]
                )
            ),
            pytest.param(
                [
                    Path("./goto_http_redirect_server/test/re6.csv"),
                    Path("./goto_http_redirect_server/test/re7.csv"),
                ],
                Re_Entry_Dict_new(
                    [
                        ("/r1", Re_Entry("/r1", "http://www.r1.com", "bob1",
                                         datetime_str("2020-01-01 00:00:00"))),
                        ("/r2", Re_Entry("/r2", "http://www.r2.com", "bob2",
                                         datetime_str("2020-01-02 00:00:00"))),
                        ("/r3", Re_Entry("/r3", "http://www.r3.com", "bob3",
                                         datetime_str("2020-01-03 00:00:00"))),
                    ]
                )
            ),
        )
    )
    def test_load_redirects_files(self,
                                  redirects_files: Path_List,
                                  expected: Re_Entry_Dict):
        actual = RedirectsLoader.load_redirects_files(redirects_files, FIELD_DELIMITER_DEFAULT)
        assert actual == expected


IP = '127.0.0.3'
PORT = 33797  # an unlikely port to be used
ENTRY_LIST = {'/a': ('b', USER, NOW)}


def port() -> int:
    """
    Use a new port for each new RedirectServer instance.

    Some CI Services images tend to keep the port open after it's use. This
    means a new RedirectServer will raise
        OSError: [Errno 98] Address already in use
    This also implies it's difficult to search for an unused port because
    that would require testing if the port can be opened.
    This is good enough.
    """
    global PORT
    PORT += 1
    return PORT


def new_redirect_handler(redirects: Re_Entry_Dict) \
        -> RedirectHandler:
    return redirect_handler_factory(
        redirects,
        REDIRECT_CODE_DEFAULT,
        '/status',
        '/reload',
        htmls('')
    )


def shutdown_server_thread(redirect_server: RedirectServer, sleep: float = 4):

    # thread target
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
Request_Thread_Return = None

req_count = 0


def request_thread(ip: str, port: int, url: str, method: str, wait: float):
    """caller should `.join` on thread"""

    # thread target
    def request_do(ip_: str, port_: int, url_: str, method_: str, wait_: float):
        time.sleep(wait_)
        cl = client.HTTPConnection(ip_, port=port_, timeout=1)
        cl.request(method_, url_)
        global Request_Thread_Return
        Request_Thread_Return = cl.getresponse()

    global req_count
    req_count += 1
    rt = threading.Thread(
        name='pytest-request_thread-%d' % req_count,
        target=request_do,
        args=(ip, port, url, method, wait))
    rt.start()
    return rt


class Test_ClassesComplex(object):

    def test_RedirectServer_server_activate(self):
        with RedirectServer((IP, port()), new_redirect_handler(ENTRY_LIST)) as redirect_server:
            redirect_server.server_activate()

    @pytest.mark.timeout(5)
    def test_RedirectServer_serve_forever(self):
        with RedirectServer((IP, port()), new_redirect_handler(ENTRY_LIST)) as redirect_server:
            _ = shutdown_server_thread(redirect_server, 1)
            redirect_server.serve_forever(poll_interval=0.3)  # blocks


class Test_LiveServer(object):
    """run the entire server which will bind to a real IP + Port"""

    F302 = int(http.HTTPStatus.FOUND)  # 302
    NF404 = int(http.HTTPStatus.NOT_FOUND)  # 404
    R308 = int(REDIRECT_CODE_DEFAULT)  # 308
    ERR501 = int(http.HTTPStatus.NOT_IMPLEMENTED)  # 501

    URL = 'http://' + IP

    rd = {'/a': Re_Entry('/a', 'A',)}

    @pytest.mark.parametrize(
        'ip, url, method, redirects, loe, hi, header',
        (
            #
            # broad checks
            #
            pytest.param(IP, URL, 'GET', {}, 200, 499, None, id='broad check GET empty'),
            pytest.param(IP, URL, 'HEAD', {}, 200, 499, None, id='broad check HEAD empty'),
            pytest.param(IP, URL + '/X', 'GET', rd, 200, 499, None, id='broad check /X GET'),
            pytest.param(IP, URL + '/X', 'HEAD', rd,  200, 499, None, id='broad check /X HEAD'),
            #
            # precise checks - typical use-cases
            #
            pytest.param(IP, URL + '/X', 'GET', rd, NF404, None, ('Location', None), id='GET Not Found'),
            pytest.param(IP, URL + '/X', 'HEAD', rd, NF404, None, ('Location', None), id='HEAD Not Found'),
            # the two happy-path Redirect Found cases
            pytest.param(IP, URL + '/a', 'GET', rd, R308, None, ('Location', 'A'), id='GET Found'),
            pytest.param(IP, URL + '/a', 'HEAD', rd, R308, None, ('Location', 'A'), id='HEAD Found'),
            # make sure empty and None redirects is handled
            pytest.param(IP, URL + '/a', 'GET', {}, NF404, None, ('Location', None), id='/a GET empty'),
            pytest.param(IP, URL + '/a', 'HEAD', {}, NF404, None, ('Location', None), id='/a HEAD empty'),
            #
            # make sure other HTTP methods do nothing
            #
            pytest.param(IP, URL, 'POST', {}, ERR501, None, None, id='POST empty'),
            pytest.param(IP, URL, 'PUT', {}, ERR501, None, None, id='PUT empty'),
            pytest.param(IP, URL, 'DELETE', {}, ERR501, None, None, id='DELETE empty'),
            pytest.param(IP, URL, 'OPTIONS', {}, ERR501, None, None, id='OPTIONS empty'),
            pytest.param(IP, URL, 'TRACE', {}, ERR501, None, None, id='TRACE empty'),
            pytest.param(IP, URL, 'PATCH', {}, ERR501, None, None, id='PATCH empty'),
            pytest.param(IP, URL + '/a', 'POST', rd, ERR501, None, None, id='POST /a'),
            pytest.param(IP, URL + '/a', 'PUT', rd, ERR501, None, None, id='PUT /a'),
            pytest.param(IP, URL + '/a', 'DELETE', rd, ERR501, None, None, id='DELETE /a'),
            pytest.param(IP, URL + '/a', 'OPTIONS', rd, ERR501, None, None, id='OPTIONS /a'),
            pytest.param(IP, URL + '/a', 'TRACE', rd, ERR501, None, None, id='TRACE /a'),
            pytest.param(IP, URL + '/a', 'PATCH', rd, ERR501, None, None, id='PATCH /a'),
            pytest.param(IP, URL + '/', 'POST', rd, ERR501, None, None, id='POST /'),
            pytest.param(IP, URL + '/.', 'POST', rd, ERR501, None, None, id='POST /.'),
        )
    )
    @pytest.mark.timeout(4)
    def test_requests(self,
                      ip: str,
                      url: str,
                      method: str,
                      redirects: typing.Optional[Re_Entry_Dict],
                      loe: int,  # low bound or equal (assertion)
                      hi: typing.Optional[int],  # high bound or None (assertion)
                      header: typing.Optional[typing.Tuple[str, str]]  # assertion
                      ):
        port_ = port()
        with RedirectServer((ip, port_), new_redirect_handler(redirects)) as redirect_server:
            # XXX: crude synchronizations. Good enough for this test harness!
            wait = 0.5
            srv_uptime = wait + 0.5
            thr_wait = wait
            shutdown_server_thread(redirect_server, srv_uptime)
            rt = request_thread(ip, port_, url, method, wait)
            redirect_server.serve_forever(poll_interval=0.2)  # blocks for srv_uptime until server is shutdown
            rt.join(thr_wait)  # blocks for thr_wait until thread ends

            # assertions
            assert not rt.is_alive(), 'thread did not end within %s seconds' % thr_wait
            global Request_Thread_Return
            assert Request_Thread_Return is not None, 'the thread did not set the global Request_Thread_Return; unlucky time synch? did the thread crash?'
            rr = Request_Thread_Return
            Request_Thread_Return = None
            if hi is None and loe:
                assert loe == rr.code
            elif hi and loe:
                assert loe <= rr.code <= hi, "ip=(%s) url=(%s) method=(%s)" % (ip, url, method)
            if header:
                assert rr.getheader(header[0]) == header[1], "getheaders: %s" % rr.getheaders()
