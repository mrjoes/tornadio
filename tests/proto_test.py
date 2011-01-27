# -*- coding: utf-8 -*-
"""
    tornadio.tests.proto_test
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

from nose.tools import eq_

from tornadio import proto

def test_encode():
    # Test string encode
    eq_(proto.encode('abc'), '~m~3~m~abc')

    # Test dict encode
    eq_(proto.encode({'a':'b'}), '~m~13~m~~j~{"a": "b"}')

    # Test list encode
    eq_(proto.encode(['a','b']), '~m~1~m~a~m~1~m~b')

    # Test unicode
    eq_(proto.encode(u'\u0430\u0431\u0432'),
        '~m~6~m~' + u'\u0430\u0431\u0432'.encode('utf-8'))

    # Test special characters encoding
    eq_(proto.encode('~m~'), '~m~3~m~~m~')

def test_decode():
    # Test string decode
    eq_(proto.decode(proto.encode('abc')), [('~m~', 'abc')])

    # Test unicode decode
    eq_(proto.decode(proto.encode(u'\u0430\u0431\u0432')),
        [('~m~', u'\u0430\u0431\u0432'.encode('utf-8'))])

    # Test JSON decode
    eq_(proto.decode(proto.encode({'a':'b'})),
        [('~m~', {'a':'b'})])

    # Test seprate messages decoding
    eq_(proto.decode(proto.encode(['a','b'])),
        [('~m~', 'a'), ('~m~', 'b')])
