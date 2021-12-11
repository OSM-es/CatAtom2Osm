# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
import mock
import unittest
import logging
logging.disable(logging.WARNING)

from catatom2osm import __main__
from test.tools import capture


def raiseIOError(*args, **kwargs):
    raise IOError('bartaz')

def raiseImportError(*args, **kwargs):
    raise ImportError('qgis')


class TestMain(unittest.TestCase):

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py'])
    def test_no_args(self):
        with capture(__main__.run) as output:
            self.assertIn("usage: catatom2osm", str(output))

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foo', 'bar'])
    @mock.patch('catatom2osm.__main__.log.error')
    def test_too_many_args(self, mocklog):
        __main__.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertIn("Too many arguments", output)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.app.CatAtom2Osm')
    def test_default(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        self.assertEqual(mockcat.call_args_list[0][0][0], 'foobar')
        options = mockcat.call_args_list[0][0][1]
        d = {'building': False, 'all': False, 'tasks': True, 'log_level': 'INFO', 
            'parcel': False, 'list': False, 'zoning': True, 'address': True}
        for (k, v) in list(d.items()):
            self.assertEqual(getattr(options, k), v)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar', '-a'])
    @mock.patch('catatom2osm.app.CatAtom2Osm')
    def test_all(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        options = mockcat.call_args_list[0][0][1]
        d = {'building': True, 'all': True, 'tasks': True, 'log_level': 'INFO', 
            'parcel': True, 'list': False, 'zoning': True, 'address': True}
        for (k, v) in list(d.items()):
            self.assertEqual(getattr(options, k), v)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar', '-b'])
    @mock.patch('catatom2osm.app.CatAtom2Osm')
    def test_building(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        options = mockcat.call_args_list[0][0][1]
        d = {'building': True, 'all': False, 'tasks': False, 'log_level': 'INFO', 
            'parcel': False, 'list': False, 'zoning': False, 'address': False}
        for (k, v) in list(d.items()):
            self.assertEqual(getattr(options, k), v)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', '-w', '33333'])
    @mock.patch('catatom2osm.app.catatom.Reader')
    def test_list(self, mockcat):
        cat = mock.MagicMock()
        mockcat.return_value = cat
        __main__.run()
        mockcat.assert_called_once_with('33333')
        cat.download.assert_has_calls([
            mock.call('address'),
            mock.call('cadastralzoning'),
            mock.call('building'),
        ])

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', '-l', '33'])
    @mock.patch('catatom2osm.app.catatom.list_municipalities')
    def test_list2(self, mocklist):
        __main__.run()
        mocklist.assert_called_once_with('33')

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', '-l', '33'])
    @mock.patch('catatom2osm.app.catatom.list_municipalities', raiseIOError)
    @mock.patch('catatom2osm.__main__.log.error')
    def test_list_error(self, mocklog):
        __main__.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertTrue(mocklog.called)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.app.CatAtom2Osm', raiseIOError)
    @mock.patch('catatom2osm.__main__.log.error')
    def test_IOError(self, mocklog):
        __main__.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertEqual(output, 'bartaz')

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.app.CatAtom2Osm', raiseImportError)
    @mock.patch('catatom2osm.__main__.log.error')
    def test_ImportError(self, mocklog):
        __main__.run()
        output1 = mocklog.call_args_list[0][0][0]
        output2 = mocklog.call_args_list[1][0][0]
        self.assertEqual(output1, 'qgis')
        self.assertIn('install QGIS', output2)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar', '--log=DEBUG'])
    @mock.patch('catatom2osm.app.CatAtom2Osm', raiseImportError)
    @mock.patch('catatom2osm.__main__.log')
    def test_debug(self, mocklog):
        mocklog.getEffectiveLevel.return_value = logging.DEBUG
        with self.assertRaises(ImportError):
            __main__.run()
        mocklog.setLevel.assert_called_once_with(logging.DEBUG)
        mocklog.error.assert_not_called()

    @mock.patch(
        'catatom2osm.__main__.sys.argv',
        ['catatom2osm.py', 'foobar', '-o', '123', '-t', '-z'],
    )
    @mock.patch('catatom2osm.app.CatAtom2Osm')
    def test_zone(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        self.assertEqual(mockcat.call_args_list[0][0][0], 'foobar')
        options = mockcat.call_args_list[0][0][1]
        d = {
            'building': True, 'all': False, 'tasks': False, 'log_level': 'INFO',
            'parcel': False, 'list': False, 'zoning': False, 'address': True,
            'zone': '123',
        }
        for (k, v) in list(d.items()):
            self.assertEqual(getattr(options, k), v)
