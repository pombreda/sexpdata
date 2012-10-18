# [[[cog import cog; cog.outl('"""\n%s\n"""' % file('README.rst').read()) ]]]
"""
S-expression parser for Python
==============================

`sexpdata` is a simple S-expression parser/serializer.  It has a
simple `load` and `dump` functions like `pickle`, `json` or `PyYAML`
module.

>>> from sexpdata import loads, dumps
>>> loads("(a b)")
[Symbol('a'), Symbol('b')]
>>> print(dumps(['a', 'b']))
("a" "b")


You can install `sexpdata` from PyPI_::

  pip install sexpdata


Links:

* `Documentaions (at Read the Docs) <http://sexpdata.readthedocs.org/>`_
* `Repository (at GitHub) <https://github.com/tkf/sexpdata>`_
* `Issue tracker (at GitHub) <https://github.com/tkf/sexpdata/issues>`_
* `PyPI <http://pypi.python.org/pypi/sexpdata>`_
* `Travis CI <https://travis-ci.org/#!/tkf/sexpdata>`_

"""
# [[[end]]]

# Copyright (c) 2012 Takafumi Arakaki
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.

# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

__version__ = '0.0.1.dev2'
__author__ = 'Takafumi Arakaki'
__license__ = 'BSD License'
__all__ = [
    # API functions:
    'load', 'loads', 'dump', 'dumps',
    # S-expression classes:
    'Symbol', 'String', 'Quoted',
]

from string import whitespace
from collections import Iterator
import functools

BRACKETS = {'(': ')', '[': ']'}


try:
    unicode
except NameError:
    basestring = unicode = str  # Python 3


### Utility

def return_as(converter):
    """
    Decorator to convert result of a function.

    It is just a function composition. The following two codes are
    equivalent.

    Using `@return_as`::

        @return_as(converter)
        def generator(args):
            ...

        result = generator(args)

    Manually do the same::

        def generator(args):
            ...

        result = converter(generator(args))

    Example:

    >>> @return_as(list)
    ... def f():
    ...     for i in range(3):
    ...         yield i
    ...
    >>> f()  # this gives a list, not an iterator
    [0, 1, 2]

    """
    def wrapper(generator):
        @functools.wraps(generator)
        def func(*args, **kwds):
            return converter(generator(*args, **kwds))
        return func
    return wrapper


### Interface

def load(filelike, **kwds):
    """
    Load object from S-expression stored in `filelike`.

    :arg  filelike: A text stream object.

    See :func:`loads` for valid keyword arguments.

    >>> import io
    >>> fp = io.StringIO()
    >>> sexp = [Symbol('a'), Symbol('b')]   # let's dump and load this object
    >>> dump(sexp, fp)
    >>> _ = fp.seek(0)
    >>> load(fp) == sexp
    True

    """
    return loads(filelike.read(), **kwds)


def loads(string, **kwds):
    """
    Load object from S-expression `string`.

    :arg        string: String containing an S-expression.
    :type          nil: str or None
    :keyword       nil: A symbol interpreted as an empty list.
                        Default is ``'nil'``.
    :type         true: str or None
    :keyword      true: A symbol interpreted as True.
                        Default is ``'t'``.

    >>> loads("(a b)")
    [Symbol('a'), Symbol('b')]
    >>> loads("a")
    Symbol('a')
    >>> loads("(a 'b)")
    [Symbol('a'), Quoted(Symbol('b'))]
    >>> loads("(a '(b))")
    [Symbol('a'), Quoted([Symbol('b')])]

    ``nil`` is converted to an empty list by default.  You can use
    keyword argument `nil` to change what symbol must be interpreted
    as nil:

    >>> loads("nil")
    []
    >>> loads("null", nil='null')
    []
    >>> loads("nil", nil=None)
    Symbol('nil')

    ``t`` is converted to True by default.  You can use keyword
    argument `true` to change what symbol must be converted to True.:

    >>> loads("t")
    True
    >>> loads("#t", true='#t')
    True
    >>> loads("t", true=None)
    Symbol('t')

    """
    obj = parse(string, **kwds)
    assert len(obj) == 1  # FIXME: raise an appropriate error
    return obj[0]


def dump(obj, filelike, **kwds):
    """
    Write `obj` as an S-expression into given stream `filelike`.

    :arg       obj: A Python object.
    :arg  filelike: A text stream object.

    See :func:`dumps` for valid keyword arguments.

    >>> import io
    >>> fp = io.StringIO()
    >>> dump([Symbol('a'), Symbol('b')], fp)
    >>> print(fp.getvalue())
    (a b)

    """
    filelike.write(unicode(dumps(obj)))


def dumps(obj, **kwds):
    """
    Convert python object into an S-expression.

    :arg           obj: A Python object.
    :keyword    str_as: How string should be interpreted.
                        Default is ``'string'``.
    :type       str_as: ``'symbol'`` or ``'string'``
    :keyword  tuple_as: How tuple should be interpreted.
                        Default is ``'list'``.
    :type     tuple_as: ``'list'`` or ``'array'``


    Basic usage:

    >>> dumps(['a', 'b'])
    '("a" "b")'
    >>> dumps(['a', 'b'], str_as='symbol')
    '(a b)'
    >>> dumps(dict(a=1, b=2))
    '(:a 1 :b 2)'

    More verbose usage:

    >>> dumps([Symbol('a'), Symbol('b')])
    '(a b)'
    >>> dumps(Symbol('a'))
    'a'
    >>> dumps([Symbol('a'), Quoted(Symbol('b'))])
    "(a 'b)"
    >>> dumps([Symbol('a'), Quoted([Symbol('b')])])
    "(a '(b))"

    """
    return tosexp(obj, **kwds)


### Core

def tosexp(obj, str_as='string', tuple_as='list'):
    _tosexp = lambda x: tosexp(x, str_as=str_as, tuple_as=tuple_as)
    if isinstance(obj, list):
        return Bracket(obj, '(').tosexp(_tosexp)
    elif isinstance(obj, tuple):
        if tuple_as == 'list':
            return Bracket(obj, '(').tosexp(_tosexp)
        elif tuple_as == 'array':
            return Bracket(obj, '[').tosexp(_tosexp)
        else:
            raise ValueError('tuple_as={0!r} is not valid'.format(tuple_as))
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, basestring):
        if str_as == 'symbol':
            return obj
        elif str_as == 'string':
            return String(obj).tosexp()
        else:
            raise ValueError("str_as={0!r} is not valid".format(str_as))
    elif isinstance(obj, dict):
        return _tosexp(dict_to_plist(obj))
    elif isinstance(obj, SExpBase):
        return obj.tosexp(_tosexp)
    else:
        raise TypeError(
            "Object of type '{0}' cannot be converted by `tosexp`. "
            "It's value is '{1!r}'".format(type(obj), obj))


@return_as(list)
def dict_to_plist(obj):
    for key in obj:
        yield Symbol(':{0}'.format(key))
        yield obj[key]


class SExpBase(object):

    def __init__(self, val):
        self._val = val

    def __repr__(self):
        return "{0}({1!r})".format(self.__class__.__name__, self._val)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._val == other._val
        else:
            return False

    def value(self):
        return self._val

    def tosexp(self, tosexp=tosexp):
        """
        Decode this object into an S-expression string.

        :arg tosexp: A function to be used when converting sub S-expression.

        """
        raise NotImplementedError


class Symbol(SExpBase):

    def tosexp(self, tosexp=None):
        return self._val


class String(SExpBase):

    _lisp_quoted_specials = [  # from Pymacs
        ('"', '\\"'), ('\\', '\\\\'), ('\b', '\\b'), ('\f', '\\f'),
        ('\n', '\\n'), ('\r', '\\r'), ('\t', '\\t')]

    def tosexp(self, tosexp=None):
        val = self._val
        for (s, q) in self._lisp_quoted_specials:
            val = val.replace(s, q)
        return '"{0}"'.format(val)


class Quoted(SExpBase):

    def tosexp(self, tosexp=tosexp):
        return "'{0}".format(tosexp(self._val))


class Bracket(SExpBase):

    def __init__(self, val, bra):
        assert bra in BRACKETS  # FIXME: raise an appropriate error
        super(Bracket, self).__init__(val)
        self._bra = bra

    def __repr__(self):
        return "{0}({1!r}, {2!r})".format(
            self.__class__.__name__, self._val, self._bra)

    def tosexp(self, tosexp=tosexp):
        bra = self._bra
        ket = BRACKETS[self._bra]
        c = ' '.join(tosexp(v) for v in self._val)
        return "{0}{1}{2}".format(bra, c, ket)


def bracket(val, bra):
    if bra == '(':
        return val
    else:
        return Bracket(val, bra)


class ExpectClosingBracket(Exception):

    def __init__(self, got, expect):
        super(ExpectClosingBracket, self).__init__(
            "Not enough closing brackets. "
            "Expected {0!r} to be the last letter in the sexp. "
            "Got: {1!r}".format(expect, got))


class ExpectNothing(Exception):

    def __init__(self, got):
        super(ExpectNothing, self).__init__(
            "Too many closing brackets. "
            "Expected no character left in the sexp. "
            "Got: {0!r}".format(got))


class LookAheadIterator(Iterator):

    def __init__(self, iterable):
        self._iter = iter(iterable)

    def next(self):
        if hasattr(self, '_next_item'):
            item = self._next_item
            del self._next_item
        else:
            item = next(self._iter)
        return item

    __next__ = next  # Python 3

    def has_next(self):
        try:
            self.lookahead()
            return True
        except StopIteration:
            return False

    def lookahead(self):
        self._next_item = self.next()
        return self._next_item

    def lookahead_safe(self, default=None):
        if self.has_next():
            return self.lookahead()
        else:
            return default


class Parser(object):

    closing_brackets = set(BRACKETS.values())
    atom_end = \
        set(BRACKETS) | set(closing_brackets) | set('"\'') | set(whitespace)

    def __init__(self, nil='nil', true='t'):
        self.nil = nil
        self.true = true

    @staticmethod
    @return_as(lambda x: String(''.join(x)))
    def parse_str(laiter):
        assert laiter.next() == '"'  # never fail
        while True:
            c = laiter.next()
            if c == '"':
                return
            elif c == '\\':
                yield c
                yield laiter.next()
            else:
                yield c

    def parse_atom(self, laiter):
        return self.atom(''.join(self._parse_atom(laiter)))

    def _parse_atom(self, laiter):
        while laiter.has_next():
            if laiter.lookahead() in self.atom_end:
                break
            yield laiter.next()

    def atom(self, token):
        if token == self.nil:
            return []
        if token == self.true:
            return True
        try:
            return int(token)
        except ValueError:
            try:
                return float(token)
            except ValueError:
                return Symbol(token)

    @return_as(list)
    def parse_sexp(self, laiter):
        while laiter.has_next():
            c = laiter.lookahead()
            if c == '"':
                yield self.parse_str(laiter)
            elif c in whitespace:
                laiter.next()
                continue
            elif c in BRACKETS:
                close = BRACKETS[c]
                laiter.next()
                yield bracket(self.parse_sexp(laiter), c)
                if laiter.lookahead_safe() != close:
                    raise ExpectClosingBracket(laiter.lookahead_safe(), close)
                laiter.next()
            elif c in self.closing_brackets:
                break
            elif c == "'":
                laiter.next()
                subsexp = self.parse_sexp(laiter)
                yield Quoted(subsexp[0])
                for sexp in subsexp[1:]:
                    yield sexp
            else:
                yield self.parse_atom(laiter)


def parse(iterable, **kwds):
    """
    Parse s-expression.

    >>> parse("(a b)")
    [[Symbol('a'), Symbol('b')]]
    >>> parse("a")
    [Symbol('a')]
    >>> parse("(a 'b)")
    [[Symbol('a'), Quoted(Symbol('b'))]]
    >>> parse("(a '(b))")
    [[Symbol('a'), Quoted([Symbol('b')])]]

    """
    laiter = LookAheadIterator(iterable)
    sexp = Parser(**kwds).parse_sexp(laiter)
    if laiter.has_next():
        raise ExpectNothing(laiter.lookahead())
    return sexp
