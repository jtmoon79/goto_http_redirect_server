#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# -*- pyversion: >=3.5.2 -*-
#
# This source code was created in-part to learn about various Python 3 features
# and useful modules:  typing, mypy, pytest, other stuff, while aiming to be
# "Pythontic". This makes for some verbose if descriptive code.


import argparse
from collections import defaultdict
import copy
import csv
import datetime
import enum
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
from typing import cast, NamedTuple
from urllib import parse
import uuid


# canonical module informations used by setup.py
__version__ = '1.1.5'
__author__ = 'jtmoon79'
__url_github__ = 'https://github.com/jtmoon79/goto_http_redirect_server'
__url_azure__ = 'https://dev.azure.com/jtmmoon/goto_http_redirect_server'
__url_circleci__ = 'https://circleci.com/gh/jtmoon79/goto_http_redirect_server'
__url_pypi__ = 'https://pypi.org/project/goto-http-redirect-server/'
__url_issues__ = 'https://github.com/jtmoon79/goto_http_redirect_server/issues'
# first line of __doc__ is used in setup.py. Should match README.md and title at
# github.com project site and Azure project site.
__doc__ = """\
The "Go To" HTTP Redirect Server for sharing dynamic shortcut URLs on your \
network.
"""

#
# globals and constants initialization needed for default values
#

USER_DEFAULT = getpass.getuser()
TIME_START = time.time()
DATETIME_START = datetime.datetime.fromtimestamp(TIME_START).\
    replace(microsecond=0)

#
# Types
# FYI: "Re" means "Redirect Entry"
#

# XXX: `from parse import ParseResult` raises ModuleNotFoundError
ParseResult = parse.ParseResult

# Redirect Entry types

Re_From = typing.NewType('Re_From', str)  # Redirect From URL Path as input from the Administrator (not modified)
Re_To = typing.NewType('Re_To', str)  # Redirect To URL Location
Re_User = typing.NewType('Re_User', str)  # User that created the Redirect (records-keeping thing, does not affect behavior)
Re_Date = typing.NewType('Re_Date', datetime.datetime)  # Datetime Redirect was created (records-keeping thing, does not affect behavior)
Re_EntryKey = Re_From  # XXX: this might be too confusing?


def Re_From_to_Re_EntryKey(from_: Re_From) -> Re_EntryKey:
    """
    Convert Re_From to Re_Entry

    XXX: not necessary anymore since class re-design
    """
    return Re_EntryKey(from_)


def to_ParseResult(value: typing.Union[str, Re_From, Re_To, Re_EntryKey]) \
        -> ParseResult:
    """
    helpful wrapper

    XXX: this is somewhat overdone since class re-design
    """
    return parse.urlparse(str(value))


@enum.unique
class Re_EntryType(enum.IntEnum):
    """a.k.a. Required Request Modifier"""

    # these must be in an order for `getEntryType_From` to succeed
    _ = 0    # /foo              ''   must start from 0
    _P = 1   # /foo;param        ';'
    _Q = 2   # /foo?query        '?'
    _PQ = 3  # /foo;param?query  ';?'
    # XXX: Disable Path Required Request Modifier
    # P =   4  # /foo/path         '/'
    # PP =  5  # /foo/path;param   '/;'
    # PQ =  6  # /foo/path?query   '/?'
    # PPQ = 7  # /foo/path;param?query '/;?'

    def __init__(self, *_):
        # XXX: Python 3.7 introduced _ignore_ but this must support Python 3.5
        #      So this is a hacky way to create these class-wide dict once.
        # XXX: *_ is required but not used. Without *_, super().__init__()
        #       raises TypeError
        #          __init__() takes 1 positional argument but 2 were given
        cls = self.__class__
        if not hasattr(cls, 'Map'):
            # create once, set once to class-wide attribute
            # XXX: using enums, e.g. cls._P, will raise AttributeError
            cls.Map = {
                0: '',
                1: ';',
                2: '?',
                3: ';?',
                # XXX: Disable Path Required Request Modifier
                # 4: '/',
                # 5: '/;',
                # 6: '/?',
                # 7: '/;?',
            }
        if not hasattr(cls, 'MapRev'):
            cls.MapRev = {v: k for k, v in cls.Map.items()}
        # XXX: Disable Path Required Request Modifier
        # if not hasattr(cls, 'Paths'):
        #     cls.Paths = (4, 5, 6, 7)
        super(cls, self).__init__()

    def getStr_EntryType(self):
        """reverse mapping of EntryType to it's required appending string"""
        return self.Map[self]

    @classmethod
    def getEntryType_From(cls, from_: Re_From):
        """the last matching Re_EntryType is the required matching"""
        required = cls._
        for typ in cls:
            if from_.endswith(cls.Map[typ]):  # type: ignore
                required = typ
        return required

    @classmethod
    def getEntryKeys(cls, from_: Re_From) -> typing.List[Re_EntryKey]:
        """
        return list of all possible Re_EntryKeys

        e.g. input '/a' returns ['/a', '/a;', '/a;?', '/a?', …]
        """

        ret = [Re_From_to_Re_EntryKey(from_)]
        et = cls.getEntryType_From(from_)
        for typ in cls:
            if et != typ:
                ret.append(
                    Re_From_to_Re_EntryKey(from_ + typ.getStr_EntryType())
                )
        return ret

    @classmethod
    def getEntryTypes_fallback(cls, typ):
        """return tuple of Re_EntryTypes in order of required fallbacks"""

        if typ == cls._:      # '/a'
            return cls._P, cls._Q, cls._PQ
        elif typ == cls._P:   # '/a;p'
            return (cls._,)   # '/a'
        elif typ == cls._PQ:  # '/a;p?q'
            return (cls._,)   # '/a'
        elif typ == cls._Q:   # '/a?q'
            return (cls._,)   # '/a'
        # XXX: Disable Path Required Request Modifier
        # elif typ == cls.P:    # '/a/b'
        #     return cls._,     # '/a'
        # elif typ == cls.PP:   # '/;'
        #     return cls._,     #
        # elif typ == cls.PPQ:  # '/;?'
        #     return cls._,     #
        # elif typ == cls.PQ:   # '/?'
        #     return cls._,     #

        raise ValueError('unmatched type value %s' % typ)

    @classmethod
    def getEntryType_ParseResult(cls, _: str, pr: ParseResult):
        # TODO: urlparse does not distinguish empty parts and non-existent parts
        #       using empty string and None.
        #       e.g. parse.urlparse('/path?') is parse.urlparse('/path')
        #       The ParseResult.query is '' in both cases but it should be None
        #       in the second case.
        #       This function should attempt to distinguish such.
        # XXX: Disable Path Required Request Modifier
        # if pr.path.count('/') > 1:
        #     if pr.params and pr.query:
        #         return cls.PPQ
        #     elif pr.params:
        #         return cls.PP
        #     elif pr.query:
        #         return cls.PQ
        #     return cls.P
        # else:
        if pr.params and pr.query:
            return cls._PQ
        elif pr.params:
            return cls._P
        elif pr.query:
            return cls._Q
        return cls._


# XXX: The entire `class Re_Entry` has a more concise declaration in
#      Python >=3.7.  The following tedium is required for Python 3.5 support.
# XXX: type annotations for NamedTuple were introduced in Python 3.6 (and cannot
#      be used here).

__Re_EntryBase = NamedTuple(
    '__Re_EntryBase',
    [
        ('from_', Re_From),
        ('to', Re_To),
        ('user', Re_User),
        ('date', datetime.datetime),
        ('from_pr', ParseResult),  # ParseResult of from_
        ('to_pr', ParseResult),    # ParseResult if to
        ('etype', Re_EntryType),
    ]
)

# XXX: setting default values for NamedTuple in Python <3.7 is also tedious.
#      Copied from https://stackoverflow.com/a/18348004/471376

__Re_EntryBase.__new__.__defaults__ = (  # type: ignore
    None,  # from_
    None,  # to
    USER_DEFAULT,  # user
    DATETIME_START,  # date
    None,  # from_pr
    None,  # to_pr
    None,  # etype
)


class Re_Entry(__Re_EntryBase):
    """
    Redirect Entry

    represents a --from-to CLI argument or one line from a redirects file
    """
    def __new__(cls, *args, **kwargs):
        """initialize `from_pr` `to_pr` based on `from_` and `to`"""

        # XXX: A tedious way to initialize default arguments that are based on
        #      other arguments. Does not check for all possible combinations of
        #      passed initializer arguments.
        #      Added to ensure correctness and to simplify pytest code.
        #
        #      Attributes of NamedTuple can not be modified after
        #      `super().__new__(…)`. And there is no typing.NamedList built-in
        #      which would allow such.
        #      Overriding via `@property def from_pr(self):` does not allow
        #      indexing among other subtle behavior differences.
        #      So settle on this somewhat ugly but workable solution.
        #
        from_ = 'from_'
        from_i = 0  # `from_` index
        from_pr = 'from_pr'
        from_val = None
        to = 'to'
        toi = 1  # `to` index
        to_pr = 'to_pr'
        etype = 'etype'
        etypei = 6  # `etype` index

        # set `from_pr` if not passed
        if len(args) < 5 and from_pr not in kwargs:
            if from_ in kwargs:
                kwargs[from_pr] = parse.urlparse(kwargs[from_])
                from_val = kwargs[from_]
            elif from_i < len(args):
                kwargs[from_pr] = parse.urlparse(args[from_i])
                from_val = args[from_i]
        # set `to_pr` if not passed
        if len(args) < 6 and to_pr not in kwargs:
            if to in kwargs:
                kwargs[to_pr] = parse.urlparse(kwargs[to])
            elif toi < len(args):
                kwargs[to_pr] = parse.urlparse(args[toi])
        # set `etype` if not passed
        if len(args) < etypei + 1 and etype not in kwargs:
            if not from_val:
                if from_ in kwargs:
                    from_val = kwargs[from_]
                elif from_i < len(args):
                    from_val = args[from_i]
            if from_val is not None:
                kwargs[etype] = Re_EntryType.getEntryType_From(from_val)

        instance = super().__new__(cls, *args, **kwargs)
        # self-check
        if instance.from_ is None:
            raise ValueError('Failed to set from_')
        if instance.to is None:
            raise ValueError('Failed to set *to*')
        if instance.from_pr is None:
            raise ValueError('Failed to set from_pr')
        if instance.to_pr is None:
            raise ValueError('Failed to set to_pr')
        if instance.etype is None:
            raise ValueError('Failed to set etype')

        return instance


# class Re_EntrySuite(MutableMapping):
#     """constrained mapping of Re_EntryType to Re_Entry"""
#
#     KEYS = [x for x in Re_EntryType]  # type: typing.List[Re_EntryType]
#
#     def __init__(self,
#                  iterable: typing.Optional[
#                      typing.Iterable[
#                          typing.Tuple[Re_EntryType, Re_Entry]
#                      ]
#                  ] = None
#                  ):
#         self._map = defaultdict(None)
#         if iterable is None:
#             return
#         for kv in iterable:
#             self.__checkkey(kv[0])
#             self._map[kv[0]] = kv[1]
#
#     def __checkkey(self, key):
#         """check key is valid, raise if not"""
#         if key not in self.KEYS:
#             raise KeyError('Given key "%s" which is not in allowed keys %s'
#                            % (key, self.KEYS))
#
#     def __getitem__(self, key):
#         self.__checkkey(key)
#         return self._map[key]
#
#     def __setitem__(self, key, value):
#         self.__checkkey(key)
#         self._map[key] = value
#
#     def __delitem__(self, key):
#         self.__checkkey(key)
#         del self._map[key]
#
#     def __iter__(self):
#         return iter(self._map.keys())
#
#     def __len__(self):
#         return len(self._map.keys())
#
#     def __bool__(self):
#         for key in self._map.keys():
#             if self._map[key]:
#                 return True
#         return False
#
#     def __repr__(self):
#         s_ = '{'
#         for key in self:
#             s_ += str(key) + ': ' + str(self._map[key]) + ','
#         s_ += '}'
#         return s_
#
#
# Re_EntryValue = Re_EntrySuite

Re_Entry_Dict = typing.NewType(
    'Re_Entry_Dict',
    typing.Dict[Re_EntryKey, Re_Entry]
)


def Re_Entry_Dict_new() -> Re_Entry_Dict:
    """type annotated empty Re_Entry_Dict"""
    return Re_Entry_Dict(dict())


Re_Field_Delimiter = typing.NewType('Re_Field_Delimiter', str)

#
# other helpful types and type aliases
# XXX: some get very pedantic because they are for learning's sake.
#

Path_List = typing.List[pathlib.Path]
FromTo_List = typing.List[typing.Tuple[str, str]]
Redirect_Counter = typing.DefaultDict[str, int]
Redirect_Code_Value = typing.NewType('Redirect_Code_Value', int)
str_None = typing.Optional[str]
Path_None = typing.Optional[pathlib.Path]
Iter_str = typing.Iterable[str]
htmls = typing.NewType('htmls', str)  # HTML String
htmls_str = typing.Union[htmls, str]


#
# further globals and constants initialization
#

PROGRAM_NAME = 'goto_http_redirect_server'
LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 80
HOSTNAME = socket.gethostname()

# default CSS for various <html>
CSS = htmls(
    """\
body {
  background-color: #2F4F4F; /* DarkSlateGray; */
  color: #FAEBD7; /* AntiqueWhite; */
  font-family: monospace;
}
@media screen and (prefers-color-scheme: light) {
  body {
    background-color: white;
    color: black;
  }
}

table td {
  border-collapse: collapse;
  border: 1px dashed;
  padding: 1px;
}
.ar {
  text-align: right;
}
tbody tr:nth-child(odd) {
  background-color: #778899; /* LightSlateGray; */
}
tbody tr:nth-child(even) {
  background-color: #708090; /* SlateGray; */
}
"""
)

# The following Javascript code has been copied from www.kryogenix.org.
#   https://www.kryogenix.org/code/browser/sorttable/sorttable.js
#   (http://archive.ph/GdD37)
# The Javascript code copied from www.kryogenix.org is licensed under
# "The MIT Licence, for code from kryogenix.org". A copy of that license is
# available at
#   https://kryogenix.org/code/browser/licence.html
#   (http://archive.ph/lvhUC)
#   project file LICENSE-www.kryogenix.org
# Code in this project, goto_http_redirect_server, is licensed under the
# terms of MIT License version outlined in file "LICENSE". The Javascript
# code copied from www.kryogenix.org is not subject that license.
# The Javascript code copied from www.kryogenix.org is subject to the
# "The MIT Licence, for code from kryogenix.org" license.
# The Javascript code copied from www.kryogenix.org has been minified.
# -- START CODE COPIED FROM www.kryogenix.org UNDER MIT LICENSE --
JAVASCRIPT_SORTABLE_JS = r"""
/*
  SortTable
  version 2
  7th April 2007
  Stuart Langridge, http://www.kryogenix.org/code/browser/sorttable/

  Instructions:
  Download this file
  Add <script src="sorttable.js"></script> to your HTML
  Add class="sortable" to any table you'd like to make sortable
  Click on the headers to sort

  Thanks to many, many people for contributions and suggestions.
  Licenced as X11: http://www.kryogenix.org/code/browser/licence.html
  This basically means: do what you want with it.
*/
var stIsIE=!1;if(sorttable={init:function(){arguments.callee.done||(arguments.callee.done=!0,_timer&&clearInterval(_timer),document.createElement&&document.getElementsByTagName&&(sorttable.DATE_RE=/^(\d\d?)[\/\.-](\d\d?)[\/\.-]((\d\d)?\d\d)$/,forEach(document.getElementsByTagName("table"),function(t){-1!=t.className.search(/\bsortable\b/)&&sorttable.makeSortable(t)})))},makeSortable:function(t){if(0==t.getElementsByTagName("thead").length&&(the=document.createElement("thead"),the.appendChild(t.rows[0]),t.insertBefore(the,t.firstChild)),null==t.tHead&&(t.tHead=t.getElementsByTagName("thead")[0]),1==t.tHead.rows.length){sortbottomrows=[];for(var e=0;e<t.rows.length;e++)-1!=t.rows[e].className.search(/\bsortbottom\b/)&&(sortbottomrows[sortbottomrows.length]=t.rows[e]);if(sortbottomrows){null==t.tFoot&&(tfo=document.createElement("tfoot"),t.appendChild(tfo));for(e=0;e<sortbottomrows.length;e++)tfo.appendChild(sortbottomrows[e]);delete sortbottomrows}headrow=t.tHead.rows[0].cells;for(e=0;e<headrow.length;e++)headrow[e].className.match(/\bsorttable_nosort\b/)||(mtch=headrow[e].className.match(/\bsorttable_([a-z0-9]+)\b/),mtch&&(override=mtch[1]),mtch&&"function"==typeof sorttable["sort_"+override]?headrow[e].sorttable_sortfunction=sorttable["sort_"+override]:headrow[e].sorttable_sortfunction=sorttable.guessType(t,e),headrow[e].sorttable_columnindex=e,headrow[e].sorttable_tbody=t.tBodies[0],dean_addEvent(headrow[e],"click",sorttable.innerSortFunction=function(t){if(-1!=this.className.search(/\bsorttable_sorted\b/))return sorttable.reverse(this.sorttable_tbody),this.className=this.className.replace("sorttable_sorted","sorttable_sorted_reverse"),this.removeChild(document.getElementById("sorttable_sortfwdind")),sortrevind=document.createElement("span"),sortrevind.id="sorttable_sortrevind",sortrevind.innerHTML=stIsIE?'&nbsp<font face="webdings">5</font>':"&nbsp;&#x25B4;",void this.appendChild(sortrevind);if(-1!=this.className.search(/\bsorttable_sorted_reverse\b/))return sorttable.reverse(this.sorttable_tbody),this.className=this.className.replace("sorttable_sorted_reverse","sorttable_sorted"),this.removeChild(document.getElementById("sorttable_sortrevind")),sortfwdind=document.createElement("span"),sortfwdind.id="sorttable_sortfwdind",sortfwdind.innerHTML=stIsIE?'&nbsp<font face="webdings">6</font>':"&nbsp;&#x25BE;",void this.appendChild(sortfwdind);theadrow=this.parentNode,forEach(theadrow.childNodes,function(t){1==t.nodeType&&(t.className=t.className.replace("sorttable_sorted_reverse",""),t.className=t.className.replace("sorttable_sorted",""))}),sortfwdind=document.getElementById("sorttable_sortfwdind"),sortfwdind&&sortfwdind.parentNode.removeChild(sortfwdind),sortrevind=document.getElementById("sorttable_sortrevind"),sortrevind&&sortrevind.parentNode.removeChild(sortrevind),this.className+=" sorttable_sorted",sortfwdind=document.createElement("span"),sortfwdind.id="sorttable_sortfwdind",sortfwdind.innerHTML=stIsIE?'&nbsp<font face="webdings">6</font>':"&nbsp;&#x25BE;",this.appendChild(sortfwdind),row_array=[],col=this.sorttable_columnindex,rows=this.sorttable_tbody.rows;for(var e=0;e<rows.length;e++)row_array[row_array.length]=[sorttable.getInnerText(rows[e].cells[col]),rows[e]];row_array.sort(this.sorttable_sortfunction),tb=this.sorttable_tbody;for(e=0;e<row_array.length;e++)tb.appendChild(row_array[e][1]);delete row_array}))}},guessType:function(t,e){sortfn=sorttable.sort_alpha;for(var r=0;r<t.tBodies[0].rows.length;r++)if(text=sorttable.getInnerText(t.tBodies[0].rows[r].cells[e]),""!=text){if(text.match(/^-?[£$¤]?[\d,.]+%?$/))return sorttable.sort_numeric;if(possdate=text.match(sorttable.DATE_RE),possdate){if(first=parseInt(possdate[1]),second=parseInt(possdate[2]),first>12)return sorttable.sort_ddmm;if(second>12)return sorttable.sort_mmdd;sortfn=sorttable.sort_ddmm}}return sortfn},getInnerText:function(t){if(!t)return"";if(hasInputs="function"==typeof t.getElementsByTagName&&t.getElementsByTagName("input").length,null!=t.getAttribute("sorttable_customkey"))return t.getAttribute("sorttable_customkey");if(void 0!==t.textContent&&!hasInputs)return t.textContent.replace(/^\s+|\s+$/g,"");if(void 0!==t.innerText&&!hasInputs)return t.innerText.replace(/^\s+|\s+$/g,"");if(void 0!==t.text&&!hasInputs)return t.text.replace(/^\s+|\s+$/g,"");switch(t.nodeType){case 3:if("input"==t.nodeName.toLowerCase())return t.value.replace(/^\s+|\s+$/g,"");case 4:return t.nodeValue.replace(/^\s+|\s+$/g,"");case 1:case 11:for(var e="",r=0;r<t.childNodes.length;r++)e+=sorttable.getInnerText(t.childNodes[r]);return e.replace(/^\s+|\s+$/g,"");default:return""}},reverse:function(t){newrows=[];for(var e=0;e<t.rows.length;e++)newrows[newrows.length]=t.rows[e];for(e=newrows.length-1;e>=0;e--)t.appendChild(newrows[e]);delete newrows},sort_numeric:function(t,e){return aa=parseFloat(t[0].replace(/[^0-9.-]/g,"")),isNaN(aa)&&(aa=0),bb=parseFloat(e[0].replace(/[^0-9.-]/g,"")),isNaN(bb)&&(bb=0),aa-bb},sort_alpha:function(t,e){return t[0]==e[0]?0:t[0]<e[0]?-1:1},sort_ddmm:function(t,e){return mtch=t[0].match(sorttable.DATE_RE),y=mtch[3],m=mtch[2],d=mtch[1],1==m.length&&(m="0"+m),1==d.length&&(d="0"+d),dt1=y+m+d,mtch=e[0].match(sorttable.DATE_RE),y=mtch[3],m=mtch[2],d=mtch[1],1==m.length&&(m="0"+m),1==d.length&&(d="0"+d),dt2=y+m+d,dt1==dt2?0:dt1<dt2?-1:1},sort_mmdd:function(t,e){return mtch=t[0].match(sorttable.DATE_RE),y=mtch[3],d=mtch[2],m=mtch[1],1==m.length&&(m="0"+m),1==d.length&&(d="0"+d),dt1=y+m+d,mtch=e[0].match(sorttable.DATE_RE),y=mtch[3],d=mtch[2],m=mtch[1],1==m.length&&(m="0"+m),1==d.length&&(d="0"+d),dt2=y+m+d,dt1==dt2?0:dt1<dt2?-1:1},shaker_sort:function(t,e){for(var r=0,o=t.length-1,n=!0;n;){n=!1;for(var s=r;s<o;++s)if(e(t[s],t[s+1])>0){var a=t[s];t[s]=t[s+1],t[s+1]=a,n=!0}if(o--,!n)break;for(s=o;s>r;--s)if(e(t[s],t[s-1])<0){a=t[s];t[s]=t[s-1],t[s-1]=a,n=!0}r++}}},document.addEventListener&&document.addEventListener("DOMContentLoaded",sorttable.init,!1),/WebKit/i.test(navigator.userAgent))var _timer=setInterval(function(){/loaded|complete/.test(document.readyState)&&sorttable.init()},10);function dean_addEvent(t,e,r){if(t.addEventListener)t.addEventListener(e,r,!1);else{r.$$guid||(r.$$guid=dean_addEvent.guid++),t.events||(t.events={});var o=t.events[e];o||(o=t.events[e]={},t["on"+e]&&(o[0]=t["on"+e])),o[r.$$guid]=r,t["on"+e]=handleEvent}}function removeEvent(t,e,r){t.removeEventListener?t.removeEventListener(e,r,!1):t.events&&t.events[e]&&delete t.events[e][r.$$guid]}function handleEvent(t){var e=!0;t=t||fixEvent(((this.ownerDocument||this.document||this).parentWindow||window).event);var r=this.events[t.type];for(var o in r)this.$$handleEvent=r[o],!1===this.$$handleEvent(t)&&(e=!1);return e}function fixEvent(t){return t.preventDefault=fixEvent.preventDefault,t.stopPropagation=fixEvent.stopPropagation,t}window.onload=sorttable.init,dean_addEvent.guid=1,fixEvent.preventDefault=function(){this.returnValue=!1},fixEvent.stopPropagation=function(){this.cancelBubble=!0},Array.forEach||(Array.forEach=function(t,e,r){for(var o=0;o<t.length;o++)e.call(r,t[o],o,t)}),Function.prototype.forEach=function(t,e,r){for(var o in t)void 0===this.prototype[o]&&e.call(r,t[o],o,t)},String.forEach=function(t,e,r){Array.forEach(t.split(""),function(o,n){e.call(r,o,n,t)})};var forEach=function(t,e,r){if(t){var o=Object;if(t instanceof Function)o=Function;else{if(t.forEach instanceof Function)return void t.forEach(e,r);"string"==typeof t?o=String:"number"==typeof t.length&&(o=Array)}o.forEach(t,e,r)}};
"""
# -- END CODE COPIED FROM www.kryogenix.org UNDER MIT LICENSE --


#
# RedirectServer class things
#

# SOCKET_LISTEN_BACKLOG is eventually passed to socket.listen
SOCKET_LISTEN_BACKLOG = 31  # type: int
STATUS_PAGE_PATH_DEFAULT = '/status'  # type: str
PATH_FAVICON = '/favicon.ico'  # type: str
REDIRECT_PATHS_NOT_ALLOWED = (PATH_FAVICON,)  # type: typing.Tuple[str]
# HTTP Status Code used for redirects (among several possible redirect codes)
REDIRECT_CODE_DEFAULT = http.HTTPStatus.TEMPORARY_REDIRECT  # type: http.HTTPStatus
REDIRECT_CODE = REDIRECT_CODE_DEFAULT  # type: http.HTTPStatus
# urlparse-related things
RE_URI_KEYWORDS = re.compile(r'\${(path|params|query|fragment)}')
URI_KEYWORDS_REPL = ('path', 'params', 'query', 'fragment')  # type: Iter_str

# signals
SIGNAL_RELOAD_UNIX = 'SIGUSR1'  # type: str
SIGNAL_RELOAD_WINDOWS = 'SIGBREAK'  # type: str
# signal to cause --redirects file reload
try:
    # Unix (not defined on Windows)
    SIGNAL_RELOAD = signal.SIGUSR1  # type: ignore # in Windows, mypy attempts import and fails
except AttributeError:
    # Windows (not defined on some Unix)
    SIGNAL_RELOAD = signal.SIGBREAK  # type: ignore # in Unix, mypy attempts import and fails

# redirect file things
FIELD_DELIMITER_DEFAULT = Re_Field_Delimiter('\t')  # type: Re_Field_Delimiter
FIELD_DELIMITER_DEFAULT_NAME = 'tab'  # type: str
FIELD_DELIMITER_DEFAULT_ESCAPED = FIELD_DELIMITER_DEFAULT.\
    encode('unicode_escape').decode('utf-8')  # type: str
REDIRECT_FILE_IGNORE_LINE = '#'  # type: str

# logging module initializations (call logging_init to complete)
LOGGING_FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S'  # type: str
LOGGING_FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'  # type: str
# importers can override 'log'
log = logging.getLogger(PROGRAM_NAME)  # type: logging.Logger

# write-once copy of sys.argv
sys_args = []  # type: typing.List[str]


#
# "volatile" global instances
#

# global list of --from-to passed redirects
Redirect_FromTo_List = []  # type: FromTo_List
# global list of --redirects files
Redirect_Files_List = []  # type: Path_List
reload_do = False  # type: bool
reload_datetime = None  # type: typing.Optional[datetime.datetime]
redirect_counter = defaultdict(int)  # type: typing.DefaultDict[str, int]
STATUS_PATH = None  # type: str_None
RELOAD_PATH = None  # type: str_None
NOTE_ADMIN = htmls('')  # type: htmls


#
# functions, classes, code
#


class StrDelay():
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
        out = ''
        if self._func:
            out = str(self._func(*self._args, **self._kwargs))
        return out


def html_escape(s_: htmls_str) -> htmls:
    """transform a Python string into equivalent HTML-displayed string"""
    return htmls(
        html.escape(s_)
            .replace('\n', '<br />\n')
            .replace('  ', r'&nbsp; ')
    )


def html_a(href: str, text: str_None = None) -> htmls:
    """create HTML <a> from href URL"""
    if text is None:
        text = href
    return htmls('<a href="' + href + '">' + html_escape(text) + '</a>')


def datetime_now() -> datetime.datetime:
    """
    Wrap datetime.now so pytests can override it.

    Also, microseconds are annoying to print so set to 0.
    """
    return datetime.datetime.now().replace(microsecond=0)


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


class RedirectHandler(server.SimpleHTTPRequestHandler):
    """
    XXX: This class is passed to RedirectServer which creates instances of
         RedirectHandler. But RedirectHandler instances need to access values
         that may change and there is not way to have RedirectServer pass some
         tuple of values to new instances. So RedirectHandler instances hold
         references to class-wide values. Those are set in the
         redirect_handler_factory by call to set_c
    """

    # override BaseHTTPRequestHandler.protocol_version to enable HTTP/1.1
    # behavior (because HTTP/1.0 is so old)
    # https://github.com/python/cpython/blob/5c02a39a0b31a330e06b4d6f44835afb205dc7cc/Lib/http/server.py#L613-L615
    protocol_version = "HTTP/1.1"

    Header_Server_Host = ('Redirect-Server-Host', HOSTNAME)
    Header_Server_Version = ('Redirect-Server-Version', __version__)
    # see https://tools.ietf.org/html/rfc2616#page-124
    Header_ContentType_html = ('Content-Type', 'text/html; charset=utf-8')
    # see https://tools.ietf.org/html/rfc2616#section-14.10
    Header_Connection_close = ('Connection', 'close')
    __count = 0

    redirects = None  # type: Re_Entry_Dict
    status_code = None  # type: http.HTTPStatus
    status_path = None  # type: str
    reload_path = None  # type: str_None
    status_path_pr = None  # type: ParseResult
    reload_path_pr = None  # type: ParseResult
    note_admin = None  # type: htmls

    @classmethod
    def set_c(cls,
              redirects: Re_Entry_Dict,
              status_code: http.HTTPStatus,
              status_path: str,
              reload_path: str_None,
              note_admin: htmls):
        """set class-wide attributes to new values"""
        cls.redirects = redirects
        cls.status_code = status_code
        cls.status_path = status_path
        cls.reload_path = reload_path
        cls.status_path_pr = parse.urlparse(cls.status_path)
        cls.reload_path_pr = parse.urlparse(str(cls.reload_path))
        cls.note_admin = note_admin

    def __init__(self, *args, **kwargs):
        RedirectHandler.__count += 1
        super().__init__(*args, **kwargs)
        log.debug('RedirectHandler.__init__ %d (0x%08X)',
                  RedirectHandler.__count, id(self))

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

    def _write_html_doc(self, html_doc: htmls) -> None:
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
        self.send_header(*self.Header_Server_Host)
        self.send_header(*self.Header_Server_Version)
        self.send_header('Content-Length', str(len(html_docb)))
        self.send_header(*self.Header_ContentType_html)
        self.send_header(*self.Header_Connection_close)
        self.end_headers()
        self.wfile.write(html_docb)

    @staticmethod
    def combine_parseresult(pr1: ParseResult, pr2: ParseResult) -> str:
        """
        Combine ParseResult parts.

        A ParseResult example is
           parse.urlparse('http://host.com/path1;parmA=a,parmB=b?a=A&b=%20B&cc=CCC#FRAG')
        returns
            ParseResult(scheme='http', netloc='host.com', path='/path1',
                        params='parm2', query='a=A&b=%20B&ccc=CCC', fragment='FRAG')

        pr1 is assumed to be a Re_To supplied at startup-time or reload-time
        pr2 is assumed to be an incoming user request

        From pr1 use .scheme, .netloc, .path
        Prefer .fragment from pr2, then pr1
        Combine .params, .query

        The RedirectEntry 'To' can use string.Template syntax to replace with
        URI parts from pr1
        For example, given RedirectEntry supplied at start-time `pr1`
           /b	http://bug-tracker.megacorp.local/search/bug.cgi?id=${query}	bob	2019-01-01 11:30:00
        A user incoming GET request for URL `pr2`
           'http://goto/b?123
        processed by `combine_parseresult` would become URL
           'http://bug-tracker.megacorp.local/search/bug.cgi?id=123'

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
            """safe subst. val, if successful replacement then pop pr2d[key]"""
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
                    # pr2d.pop(key)
                # log.debug('    "%s": "%s" -> "%s"  POP? %s', key, val_old, val, popd)
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

        url = parse.urlunparse(ParseResult(**pr))
        return url

    @staticmethod
    def query_match(pr1: ParseResult, pr2: ParseResult) -> bool:
        """
        :param pr1: was supplied at startup-time or reload-time
        :param pr2: is a ppq incoming user request: path + parameters + query
        """
        # TODO: how should this interact with path required modifier?
        return pr1.path == pr2.path

    @staticmethod
    def query_match_finder(ppq: str,
                           ppqpr: ParseResult,
                           redirects: Re_Entry_Dict) \
            -> typing.Optional[Re_Entry]:
        """
        An incoming query can have multiple matches within redirects. Return the
        required request matching entry.

        For example, given incoming ppq '/foo?a=1' and redirects
            {
                '/foo': …
                '/foo?': …
                '/foo;': …
            }
        This could match keys '/foo' and '/foo?' (not '/foo;'). This will return
        the entry for required request match of '/foo?'.

        :param ppq: incoming user request
        :param ppqpr: same incoming user request as ParseResult
        :param redirects: loaded redirect entries
        """
        path = ppqpr.path
        keys = []
        keyt = []
        ppqt = Re_EntryType.getEntryType_ParseResult(ppq, ppqpr)
        # search for all possible entry based on path;
        # e.g.
        #     '/foo', '/foo;', '/foo;?', '/foo?'

        # search for exact match, accumulate possible matches as it goes
        for key in Re_EntryType.getEntryKeys(typing.cast(Re_From, path)):
            # XXX: Disable Path Required Request Modifier
            # if ppqt in (Re_EntryType.Paths):
            #     key = key.split('/')[:1].join('')
            if key not in redirects:
                continue
            entry = redirects[key]
            if entry.etype == ppqt:
                return entry  # shortcut remaining matching
            keys.append(key)
            keyt.append(entry.etype)

        # nothing is a possible match
        if not keys:
            return None

        # search for inexact but appropriate type match
        for typ in Re_EntryType.getEntryTypes_fallback(ppqt):
            if typ in keyt:
                return redirects[keys[keyt.index(typ)]]

        # XXX: no fallback was found yet there were fallback keys? concerning.
        log.error('Expected to find fallback type for type %s', ppqt)
        return None

    def do_GET_status(self, note_admin: htmls) -> None:
        """dump status information about this server instance"""

        http_sc = http.HTTPStatus.OK  # HTTP Status Code
        self.log_message('status requested, returning %s (%s)',
                         int(http_sc), http_sc.phrase,
                         loglevel=logging.INFO)
        self.send_response(http_sc)
        he = html_escape  # abbreviate

        # create the html body
        esc_title = he(
            '%s status' % PROGRAM_NAME)
        start_datetime = datetime.datetime.\
            fromtimestamp(TIME_START).replace(microsecond=0)
        uptime = time.time() - TIME_START
        esc_overall = \
            'Program {}'.format(
                html_a(__url_github__, PROGRAM_NAME)
            )
        esc_overall += he(' version {}.\n'.format(__version__))
        esc_overall += he(
            'Process ID %s listening on %s:%s on host %s\n'
            'Process start datetime %s (up time %s)\n'
            'Successful Redirect Status Code is %s (%s)'
            % (os.getpid(), self.server.server_address[0],
               self.server.server_address[1], HOSTNAME,
               start_datetime, datetime.timedelta(seconds=uptime),
               int(self.status_code), self.status_code.phrase,)
        )

        def obj_to_html(obj, sort_keys=False) -> htmls:
            """Convert an object to html"""
            return he(
                json.dumps(obj, indent=2, ensure_ascii=False,
                           sort_keys=sort_keys, default=str)
            )

        def redirects_to_html_table(rd: Re_Entry_Dict, reload_datetime_) \
                -> htmls:
            """Convert Re_Entry_Dict into linkable html table"""
            esc_reload_datetime = he(cast(datetime.datetime, reload_datetime_)
                                     .isoformat())
            s_ = """\
<table class="sortable">
    <caption>Currently Loaded Redirects (last reload {esc_reload_datetime})</caption>
    <thead>
        <tr>
            <th scope="col">From</th><th scope="col">To</th><th scope="col" class="ar">Entry User</th><th scope="col">Entry datetime</th>
        </tr>
    </thead>
    <tbody>
""".format(esc_reload_datetime=esc_reload_datetime)
            for key in rd.keys():
                val = rd[key]
                s_ += """\
        <tr>
            <td>{from_}</td><td>{to_}</td><td class="ar">{user}</td><td>{date}</td>
        </tr>
"""\
                    .format(from_=html_a(val.from_),
                            to_=he(val.to),
                            user=he(val.user),
                            date=he(str(val.date)),
                            )
            s_ += """\
    </tbody>
</table>"""
            return htmls(s_)

        esc_reload_info = he(
            ' (process signal %d (%s))' % (SIGNAL_RELOAD, SIGNAL_RELOAD)
        )
        esc_redirects_counter = obj_to_html(redirect_counter)
        esc_redirects = redirects_to_html_table(self.redirects, reload_datetime)
        esc_files = obj_to_html(Redirect_Files_List)
        if note_admin:
            note_admin = htmls('\n    <div>\n') + note_admin + htmls('\n    </div>\n')  # type: ignore
        html_doc = htmls(
            r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>{esc_title}</title>
    <style type="text/css">
        /* <!-- */
{css}
        /* --> */
    </style>
    <script>
        // <!--
{javascript}
        // -->
    </script>
</head>
<body>
<!-- begin status-page-file note -->{note}<!-- end status-page-file note -->
<div>
{esc_redirects}
</div>
<div>
    <h3>Redirect Files Searched During an Reload{esc_reload_info}:</h3>
    <pre>
{esc_files}
    </pre>
</div>
<div>
    <h3>Redirects Counter:</h3>
    Counting of successful redirect responses:
    <pre>
{esc_redirects_counter}
    </pre>
    <h3>Process Information:</h3>
    <pre>
{esc_overall}
    </pre>
</div>
</body>
</html>"""
            .format(esc_title=esc_title,
                    css=CSS,
                    javascript=JAVASCRIPT_SORTABLE_JS,
                    note=note_admin,
                    esc_redirects=esc_redirects,
                    esc_reload_info=esc_reload_info,
                    esc_files=esc_files,
                    esc_redirects_counter=esc_redirects_counter,
                    esc_overall=esc_overall)
        )
        self._write_html_doc(html_doc)

    def do_GET_reload(self) -> None:
        http_sc = http.HTTPStatus.ACCEPTED  # HTTP Status Code
        self.log_message('reload requested, returning %s (%s)',
                         int(http_sc), http_sc.phrase,
                         loglevel=logging.INFO)
        esc_datetime = html_escape(datetime_now().isoformat())
        self.send_response(http_sc)
        esc_title = html_escape('%s reload' % PROGRAM_NAME)
        html_doc = htmls(
            r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{esc_title}</title>
<style type="text/css">
        /* <!-- */
{css}
        /* --> */
</style>
</head>
<body>
Reload request accepted at {esc_datetime}.
</body>
</html>\
"""
            .format(esc_title=esc_title,
                    css=CSS,
                    esc_datetime=esc_datetime
                    )
        )
        self._write_html_doc(html_doc)
        global reload_do
        reload_do = True

    def do_GET_redirect_NOT_FOUND(self,
                                  ppq: str,
                                  ppqpr: ParseResult) -> None:
        """a Redirect request was not found, return some HTML to the user"""

        self.send_response(http.HTTPStatus.NOT_FOUND)
        esc_title = html_escape("Not Found - '%s'" % ppqpr.path[:64])
        esc_ppq = html_escape(ppq)
        html_doc = htmls("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{esc_title}</title>
<style type="text/css">
{css}
</style>
</head>
<body>
Redirect Path not found: <code>{esc_ppq}</code>
</body>
</html>\
"""
        .format(esc_title=esc_title,
                css=CSS,
                esc_ppq=esc_ppq)
        )
        self._write_html_doc(html_doc)

    def do_HEAD_redirect_NOT_FOUND(self) -> None:
        self.send_response(http.HTTPStatus.NOT_FOUND)
        self.send_header(*self.Header_Server_Host)
        self.send_header(*self.Header_Server_Version)
        self.send_header(*self.Header_ContentType_html)  # https://tools.ietf.org/html/rfc2616#page-124
        self.send_header(*self.Header_Connection_close)
        self.end_headers()

    def do_HEAD_nothing(self) -> None:
        self.send_response(http.HTTPStatus.FOUND)
        self.send_header(*self.Header_Server_Host)
        self.send_header(*self.Header_Server_Version)
        self.send_header(*self.Header_ContentType_html)  # https://tools.ietf.org/html/rfc2616#page-124
        self.send_header(*self.Header_Connection_close)
        self.end_headers()

    def _do_VERB_redirect(self,
                          ppq: str,
                          ppqpr: ParseResult,
                          redirects_: Re_Entry_Dict) -> None:
        """
        handle the HTTP Redirect Request (the entire purpose of this
        script).  Used for GET and HEAD requests.
        HEAD requests must not have a body (among many other differences
        in GET and HEAD behavior).
        """
        entry_ = RedirectHandler.query_match_finder(ppq, ppqpr, redirects_)
        if entry_ is None:
            self.log_message(
                'no redirect found for incoming (%s), returning %s (%s)',
                ppq,
                int(http.HTTPStatus.NOT_FOUND),
                http.HTTPStatus.NOT_FOUND.phrase,
                loglevel=logging.INFO)
            cmd = self.command.upper()
            if cmd == 'GET':
                return self.do_GET_redirect_NOT_FOUND(ppq, ppqpr)
            elif cmd == 'HEAD':
                return self.do_HEAD_redirect_NOT_FOUND()
            log.error('Unhandled command "%s"', cmd)
            return
        entry = entry_  # type: ignore

        # merge RedirectEntry URI parts with incoming requested URI parts
        to = self.combine_parseresult(entry.to_pr, ppqpr)
        user = entry.user
        dt = entry.date

        self.log_message('redirect found (%s) → (%s), returning %s (%s)',
                         ppqpr.path, to,
                         int(self.status_code), self.status_code.phrase,
                         loglevel=logging.INFO)

        self.send_response(self.status_code)
        self.send_header(*self.Header_Server_Host)
        self.send_header(*self.Header_Server_Version)
        # The 'Location' Header is used by browsers for HTTP 30X Redirects
        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Location
        # The most important statement in this program.
        self.send_header('Location', to)
        try:
            self.send_header('Redirect-Created-By', user)
        except UnicodeEncodeError:
            log.exception('header "Redirect-Created-By" set to fallback')
            self.send_header('Redirect-Created-By', 'Error Encoding User')
        self.send_header('Redirect-Created-Date', dt.isoformat())
        self.send_header(*self.Header_Connection_close)
        # TODO: https://tools.ietf.org/html/rfc2616#section-10.3.2
        #       the entity of the response SHOULD contain a short hypertext
        #       note with a hyperlink to the new URI(s)
        self.end_headers()
        # Do Not Write HTTP Content
        redirect_counter[str(ppqpr.path)] += 1

    def _do_VERB_log(self):
        """simple helper"""
        print_debug('')
        try:
            self.log_message(
                '\n  self: %s (0x%08X)\n  self.client_address: %s\n  '
                'self.command: %s\n  self.path: "%s"\n  '
                'self.headers:\n    %s',
                type(self), id(self), self.client_address,
                self.command, self.path,
                str(self.headers).strip('\n').replace('\n', '\n    '),
            )
        except Exception:
            log.exception('Failed to log request')

    def do_GET(self) -> None:
        """
        baseclass invokes per HTTP GET Request (request entrypoint)

        XXX: self.path in baseclass is poorly named. It is a combination of path
             query, and parameters.
        NOTE: Fragments are often dropped by clients.
        """
        self._do_VERB_log()

        ppq = self.path
        ppqpr = to_ParseResult(ppq)
        if self.query_match(self.status_path_pr, ppqpr):
            self.do_GET_status(self.note_admin)
            return
        elif self.query_match(self.reload_path_pr, ppqpr):
            self.do_GET_reload()
            return

        self._do_VERB_redirect(ppq, ppqpr, self.redirects)

    def do_HEAD(self) -> None:
        """
        baseclass invokes per HTTP HEAD Request (request entrypoint)

        XXX: self.path in baseclass is poorly named. It is a combination of path
             query, and parameters.
        NOTE: Fragments are often dropped by clients.
        """
        self._do_VERB_log()

        ppq = self.path
        ppqpr = to_ParseResult(ppq)
        if self.query_match(self.status_path_pr, ppqpr):
            self.do_HEAD_nothing()
            return
        elif self.query_match(self.reload_path_pr, ppqpr):
            self.do_HEAD_nothing()
            return

        self._do_VERB_redirect(ppq, ppqpr, self.redirects)


def redirect_handler_factory(redirects: Re_Entry_Dict,
                             status_code: http.HTTPStatus,
                             status_path: str,
                             reload_path: str_None,
                             note_admin: htmls):
    """
    :param redirects: dictionary of from-to redirects for the server
    :param status_code: HTTPStatus instance to use for successful redirects
    :param status_path: server status page path
    :param reload_path: reload request path
    :param note_admin: status page note HTML
    :return: RedirectHandler type: request handler class type for
             RedirectServer.RequestHandlerClass
    """
    log.debug('using redirect dictionary (0x%08x) with %s entries:\n%s',
              id(redirects), len(redirects),
              StrDelay(pprint.pformat, redirects, indent=2))

    rh = RedirectHandler
    rh.set_c(redirects, status_code, status_path, reload_path, note_admin)

    return rh


class RedirectsLoader(object):
    """a namespace for functions that load and initialize Redirect Entries"""

    @staticmethod
    def load_redirects_fromto(from_to: FromTo_List) -> Re_Entry_Dict:
        """
        create Re_Entry for each --from-to passed
        :return: Re_Entry_Dict
        """

        user = USER_DEFAULT
        now = datetime_now()
        entrys = Re_Entry_Dict_new()
        for ft in from_to:
            from_ = Re_From(ft[0])
            to_ = Re_To(ft[1])
            key = Re_From_to_Re_EntryKey(from_)
            typ = Re_EntryType.getEntryType_From(from_)
            val = Re_Entry(
                from_,
                to_,
                Re_User(user),
                Re_Date(now),
                etype=typ,
            )
            entrys[key] = val
        return entrys

    @staticmethod
    def load_redirects_files(redirects_files: Path_List,
                             field_delimiter: Re_Field_Delimiter) \
            -> Re_Entry_Dict:
        """
        :param redirects_files: list of file paths to process for Re_Entry
        :param field_delimiter: passed to csv.reader keyword delimiter
        :return: Re_Entry_Dict of file line items converted to Re_Entry
        """

        entrys = Re_Entry_Dict_new()

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
                            from_ = Re_From(row[0])
                            to_ = Re_To(row[1])
                            user = Re_User(row[2])
                            date = row[3]
                            # ignore any remaining fields in row
                            dt = fromisoformat(date)
                            key = Re_From_to_Re_EntryKey(from_)
                            typ = Re_EntryType.getEntryType_From(from_)
                            val = Re_Entry(
                                from_,
                                to_,
                                user,
                                Re_Date(dt),
                                etype=typ,
                            )
                            entrys[key] = val
                        except Exception:
                            log.exception('Error processing row %d of file %s',
                                          csvr.line_num, rfilen)
            except Exception:
                log.exception('Error processing file %s', rfilen)

        return entrys

    @staticmethod
    def clean_redirects(entrys: Re_Entry_Dict) -> Re_Entry_Dict:
        """remove entries with To paths that are reserved or cannot encode"""

        # TODO: process re_entry for circular loops of redirects, either
        #       break those loops or log.warning
        #       e.g. given redirects '/a' → '/b' and '/b' → '/a',
        #       the browser will (in theory) redirect forever.
        #       (browsers tested force stopped the redirect loop; Edge, Chrome).

        for path in REDIRECT_PATHS_NOT_ALLOWED:
            key = Re_From_to_Re_EntryKey(Re_From(path))
            if key in entrys.keys():
                log.warning(
                    'Removing reserved From value "%s" from redirect entries.',
                    path
                )
                entrys.pop(key)

        # check for To "Location" Header values that will fail to encode
        remove = []
        encoding = 'latin-1'
        for key in entrys.keys():
            # test "Location" header value before send_response(status_code)
            to = entrys[key].to
            try:
                # this is done in standard library http/server.py
                # method BaseServer.send_header
                # https://github.com/python/cpython/blob/5c02a39a0b31a330e06b4d6f44835afb205dc7cc/Lib/http/server.py#L515-L516
                to.encode(encoding, 'strict')
            except UnicodeEncodeError:
                remove.append(key)
        for key in remove:
            to = entrys[key].to
            log.warning(
                'Removing To "Location" value "%s"; it fails encoding to'
                ' "%s"', to, encoding
            )
            del entrys[key]

        return entrys

    @staticmethod
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
        entrys_fromto = RedirectsLoader.load_redirects_fromto(from_to)
        entrys_files = RedirectsLoader.load_redirects_files(redirects_files,
                                                            field_delimiter)
        # --from-to passed entries override same entries from files
        entrys_files.update(entrys_fromto)

        entrys_files = RedirectsLoader.clean_redirects(entrys_files)

        return entrys_files


class RedirectServer(socketserver.ThreadingTCPServer):
    """
    Custom Server to allow reloading redirects while serve_forever.
    """
    field_delimiter = FIELD_DELIMITER_DEFAULT

    def __init__(self, *args):
        """adjust parameters of the Parent class"""
        # self.allow_reuse_address = True
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
        return super(socketserver.ThreadingTCPServer, self).shutdown()

    def service_actions(self):
        """
        Override function.

        Polled during socketserver.TCPServer.serve_forever.
        Checks global reload and create new handler (which will re-read
        the Redirect_Files_List)

        TODO: avoid use of globals, somehow pass instance variables to this
              function or class instance
        """

        super(RedirectServer, self).service_actions()

        global reload_do
        if not reload_do:
            return
        reload_do = False
        global Redirect_FromTo_List
        global Redirect_Files_List
        entrys = RedirectsLoader.load_redirects(
            Redirect_FromTo_List,
            Redirect_Files_List,
            self.field_delimiter
        )
        global STATUS_PATH
        global reload_datetime
        global RELOAD_PATH
        global NOTE_ADMIN
        reload_datetime = datetime_now()
        redirect_handler = redirect_handler_factory(entrys,
                                                    REDIRECT_CODE,
                                                    STATUS_PATH,
                                                    RELOAD_PATH,
                                                    NOTE_ADMIN)
        pid = os.getpid()
        log.debug(
            "reload %s (0x%08x)\n"
            "new RequestHandlerClass (0x%08x) to replace old (0x%08x)\n"
            "PID %d",
            reload_do, id(reload_do),
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
    global reload_do
    log.debug(
        'reload_signal_handler: Signal Number %s, reload_do %s (0x%08x)',
        signum, reload_do, id(reload_do))
    reload_do = True


def process_options() -> typing.Tuple[str,
                                      int,
                                      bool,
                                      Path_None,
                                      str,
                                      str,
                                      Redirect_Code_Value,
                                      int,
                                      Re_Field_Delimiter,
                                      Path_None,
                                      FromTo_List,
                                      typing.List[str]]:
    """Process script command-line options."""

    rcd = REDIRECT_CODE_DEFAULT  # abbreviate
    global sys_args
    sys_args = copy.copy(sys.argv)  # set once

    parser = argparse.ArgumentParser(
        description=__doc__ + """\

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
                             ' --from-to "/hr" "http://human-resources.megacorp.local/login"',
                        default=list())

    pgroup = parser.add_argument_group(title='Network Options')
    pgroup.add_argument('--ip', '-i', action='store', default=LISTEN_IP,
                        help='IP interface to listen on.'
                             ' Default is %(default)s .')
    pgroup.add_argument('--port', '-p', action='store', type=int,
                        default=LISTEN_PORT,
                        help='IP port to listen on.'
                             ' Default is %(default)d .')

    pgroup = parser.add_argument_group(title='Server Options')
    pgroup.add_argument('--status-path', action='store',
                        default=STATUS_PAGE_PATH_DEFAULT, type=str,
                        help='The status path'
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
    rc_307 = http.HTTPStatus.TEMPORARY_REDIRECT
    rc_308 = http.HTTPStatus.PERMANENT_REDIRECT
    pgroup.add_argument('--redirect-code', action='store',
                        default=int(rcd), type=int,
                        help='Set HTTP Redirect Status Code as an'
                             ' integer. Most often the desired override will'
                             ' be ' + str(int(rc_307)) +  # NOQA
                             ' (' + rc_307.phrase +  # NOQA
                             '). Keep in mind, Status Code ' + rc_308.phrase +  # NOQA
                             ' will cause most browsers to cache the redirect.'
                             'Any HTTP Status Code could be used but odd'
                             ' things will happen if a value like 500 is'
                             ' returned.'
                             ' This Status Code is only returned when a'
                             ' loaded redirect entry is found and returned.'
                             ' Default successful redirect Status Code is'
                             ' %(default)s (' + rcd.phrase + ').')
    pgroup.add_argument('--field-delimiter', action='store',
                        default=FIELD_DELIMITER_DEFAULT,
                        help='Field delimiter string for --redirects files'
                             ' per-line redirect entries.'
                             ' Default is "' +  # NOQA
                             FIELD_DELIMITER_DEFAULT_ESCAPED +  # NOQA
                             '" (ordinal ' +  # NOQA
                             str(ord(FIELD_DELIMITER_DEFAULT[0])) + ').'
                        )
    assert len(FIELD_DELIMITER_DEFAULT) == 1,\
        '--help is wrong about default FIELD_DELIMITER'
    pgroup.add_argument('--status-note-file', action='store', type=str,
                        help='Status page note: Filesystem path to a file with'
                             ' HTML that will be embedded within a <div>'
                             ' element in the status page.')
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

    /hr{fd}http://human-resources.megacorp.local/login{fd}bob{fd}2019-09-07 12:00:00

  The last two fields, "added by user" and "added on datetime", are intended
  for record-keeping within an organization.

  A passed redirect should have a leading "/" as this is the URI path given for
  processing.
  For example, the URL "http://host/hr" is processed as URI path "/hr".

  A redirect will combine the various incoming URI parts.
  For example, given redirect entry:

    /b{fd}http://bug-tracker.megacorp.local/view.cgi{fd}bob{fd}2019-09-07 12:00:00

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

    /b{fd}http://bug-tracker.megacorp.local/view.cgi?id=${query}{fd}bob{fd}2019-09-07 12:00:00

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

    /b?{fd}http://bug-tracker.megacorp.local/view.cgi?id=${query}{fd}bob{fd}2019-09-07 12:00:00
    /b{fd}http://bug-tracker.megacorp.local/main{fd}bob{fd}2019-09-07 12:00:00

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

    /b?{fd}http://bug-tracker.megacorp.local/view.cgi?id=${query}{fd}bob{fd}2019-09-07 12:00:00

  and the incoming GET or HEAD request:

    http://goto/b

  will return 404 NOT FOUND.

  Required Request Modifiers must be at the end of the "from path" field string.
  Required Request Modifiers strings are:

     ';'  for user requests with a parameter.
     '?'  for user requests with a query.
     ';?' for user requests with a parameter and a query.

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

About this program:

  Modules used are available within the standard CPython distribution.
  Written for Python 3.7 but hacked to run with at least Python 3.5.2.

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

    status_note_file = None
    if args.status_note_file:
        status_note_file = pathlib.Path(args.status_note_file)

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
        status_note_file, \
        args.from_to, \
        redirects_files


def main() -> None:
    """
    default module entry point
    """
    ip, \
        port, \
        log_debug, \
        log_filename, \
        status_path, \
        reload_path, \
        redirect_code, \
        shutdown, \
        field_delimiter, \
        status_note_file, \
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
    entry_list = RedirectsLoader.load_redirects(
        Redirect_FromTo_List,
        Redirect_Files_List,
        field_delimiter
    )
    global reload_datetime
    reload_datetime = datetime_now()

    if len(entry_list) < 1:
        log.warning('There are no redirect entries')

    global STATUS_PATH
    STATUS_PATH = status_path
    log.debug('status_path (%s)', STATUS_PATH)

    global RELOAD_PATH
    RELOAD_PATH = reload_path
    log.debug('reload_path (%s)', RELOAD_PATH)

    redirect_code_ = http.HTTPStatus(int(redirect_code))
    global REDIRECT_CODE
    REDIRECT_CODE = redirect_code_
    log.debug('Successful Redirect Status Code is %s (%s)', int(REDIRECT_CODE),
              REDIRECT_CODE.phrase)

    global NOTE_ADMIN
    if status_note_file:
        log.debug('reading --status-note-file (%s)', status_note_file)
        note_s = open(str(status_note_file)).read()
        NOTE_ADMIN = htmls(note_s)
        log.debug('read %d characters from --status-note-file', len(NOTE_ADMIN))

    # register the signal handler function
    log.debug('Register handler for signal %d (%s)',
              SIGNAL_RELOAD, SIGNAL_RELOAD)
    signal.signal(SIGNAL_RELOAD, reload_signal_handler)

    do_shutdown = False  # flag between threads MainThread and shutdown_thread

    def shutdown_server(redirect_server_: RedirectServer, shutdown_: int):
        """Thread entry point"""
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
    redirect_handler = redirect_handler_factory(entry_list,
                                                REDIRECT_CODE,
                                                STATUS_PATH,
                                                RELOAD_PATH,
                                                NOTE_ADMIN)
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
