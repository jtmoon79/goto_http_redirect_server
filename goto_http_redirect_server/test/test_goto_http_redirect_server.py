#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-


__author__ = 'jtmoon79'
__doc__ = \
    """Test the goto_http_redirect_server project using pytest."""

from collections import defaultdict
from urllib.parse import ParseResult

import pytest

from goto_http_redirect_server.goto_http_redirect_server import (
    html_escape,
    htmls,
    combine_parseresult,
)

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


class Test_Functions(object):

    @pytest.mark.parametrize(
        's_,'
        'expected',
        (
            pytest.param(
                '',
                htmls(''),
            ),
            pytest.param(
                'A',
                htmls('A'),
            ),
            pytest.param(
                '&',
                htmls('&amp;'),
            ),
            pytest.param(
                '<>',
                htmls('&lt;&gt;'),
            ),
            pytest.param(
                'foo\nbar',
                htmls('foo<br />\nbar'),
            ),
        )
    )
    def test_html_escape(self,
                         s_,
                         expected):
        actual = html_escape(s_)
        assert expected == actual
        assert type(expected) == type(actual)


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
