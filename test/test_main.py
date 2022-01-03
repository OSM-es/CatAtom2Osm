# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import str
from argparse import Namespace
import logging
import mock
import os
import unittest
logging.disable(logging.WARNING)

from catatom2osm import __main__, config
from test.tools import capture
os.environ['LANGUAGE'] = 'C'
config.install_gettext('catato2osm', '')


def raiseIOError(*args, **kwargs):
    raise IOError('bartaz')

def raiseImportError(*args, **kwargs):
    raise ImportError('qgis')


class TestMain(unittest.TestCase):

    def setUp(self):
        self.options = Namespace(
            zone=[], all=False, tasks=True, zoning=True, building=False,
            address=True, comment=False, download=False, list=False,
            list_zones=False, log_level='INFO', manual=False, parcel=False,
            path=['foobar'], split=None,
        )

    def compareOptions(self, options):
        for (k, v2) in self.options.__dict__.items():
            v1 = getattr(options, k)
            self.assertEqual(v1, v2, msg='%s != %s in option %s' % (v1, v2, k))

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py'])
    def test_no_args(self):
        with capture(__main__.run) as output:
            self.assertIn("usage: catatom2osm", str(output))

    @mock.patch(
        'catatom2osm.__main__.sys.argv',
        ['catatom2osm.py', 'foo', 'bar', '-o', '1', '2']
    )
    @mock.patch('catatom2osm.__main__.log.error')
    def test_too_many_args(self, mocklog):
        __main__.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertIn("Can't use multiple zones", output)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm.create_and_run')
    def test_default(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        self.assertEqual(mockcat.call_args_list[0][0][0], 'foobar')
        options = mockcat.call_args_list[0][0][1]
        self.compareOptions(options)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar', '-a'])
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm.create_and_run')
    def test_all(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        options = mockcat.call_args_list[0][0][1]
        self.options.building = True
        self.options.parcel = True
        self.options.all = True
        self.compareOptions(options)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar', '-b'])
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm.create_and_run')
    def test_building(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        options = mockcat.call_args_list[0][0][1]
        self.options.building = True
        self.options.tasks = False
        self.options.zoning = False
        self.options.address = False
        self.compareOptions(options)

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
        self.assertTrue(mocklog.called)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm')
    @mock.patch('catatom2osm.__main__.log.error')
    def test_IOError(self, mocklog, mockcat):
        mockcat.create_and_run = raiseIOError
        __main__.run()
        output = mocklog.call_args_list[0][0][0]
        self.assertEqual(output, 'bartaz')

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar'])
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm')
    @mock.patch('catatom2osm.__main__.log.error')
    def test_ImportError(self, mocklog, mockcat):
        mockcat.create_and_run = raiseImportError
        __main__.run()
        output1 = mocklog.call_args_list[0][0][0]
        output2 = mocklog.call_args_list[1][0][0]
        self.assertEqual(output1, 'qgis')
        self.assertIn('install QGIS', output2)

    @mock.patch('catatom2osm.__main__.sys.argv', ['catatom2osm.py', 'foobar', '--log=DEBUG'])
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm')
    @mock.patch('catatom2osm.__main__.log')
    def test_debug(self, mocklog, mockcat):
        mockcat.create_and_run = raiseImportError
        mocklog.getEffectiveLevel.return_value = logging.DEBUG
        with self.assertRaises(ImportError):
            __main__.run()
        mocklog.setLevel.assert_called_once_with(logging.DEBUG)
        mocklog.error.assert_not_called()

    @mock.patch(
        'catatom2osm.__main__.sys.argv',
        ['catatom2osm.py', 'foobar', '-o', '123', '-t', '-z'],
    )
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm.create_and_run')
    def test_zone(self, mockcat):
        __main__.run()
        self.assertTrue(mockcat.called)
        self.assertEqual(mockcat.call_args_list[0][0][0], 'foobar')
        options = mockcat.call_args_list[0][0][1]
        self.options.zone = ['123']
        self.compareOptions(options)

    @mock.patch(
        'catatom2osm.__main__.sys.argv',
        ['catatom2osm.py', '11111', '22222', '33333'],
    )
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm.create_and_run')
    def test_multi(self, mockcat):
        options = Namespace(
            zone=[], all=False, tasks=True, zoning=True, building=False,
            address=True, comment=False, download=False, list=False,
            list_zones=False, log_level='INFO', manual=False, parcel=False,
            path=['11111', '22222', '33333'],
        )
        self.options.path = ['11111', '22222', '33333']
        __main__.run()
        mockcat.assert_has_calls([
            mock.call('11111', self.options),
            mock.call('22222', self.options),
            mock.call('33333', self.options),
        ])

    @mock.patch(
        'catatom2osm.__main__.sys.argv',
        ['catatom2osm.py', 'foobar', '-o', '1', '2', '3'],
    )
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm.create_and_run')
    def test_zones(self, mockcat):
        self.options.zone = ['1', '2', '3']
        __main__.run()
        mockcat.assert_called_with('foobar', self.options)

    @mock.patch(
        'catatom2osm.__main__.sys.argv',
        ['catatom2osm.py', '-o', '1', '2', '3', 'foobar'],
    )
    @mock.patch('catatom2osm.app.QgsSingleton', mock.MagicMock)
    @mock.patch('catatom2osm.app.CatAtom2Osm.create_and_run')
    def test_zones2(self, mockcat):
        self.options.zone = ['1', '2', '3']
        __main__.run()
        mockcat.assert_called_with('foobar', self.options)
