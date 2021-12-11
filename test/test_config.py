from __future__ import unicode_literals
import unittest
import os

from catatom2osm import config

class TestSetup(unittest.TestCase):

    def test_win(self):
        eol = config.eol
        lang = os.getenv('LANG')
        config.platform = 'linux2'
        config.winenv()
        self.assertEqual(config.eol, '\n')
        config.platform = 'winx'
        config.winenv()
        self.assertEqual(config.eol, '\r\n')
        config.language = 'foobar'
        del os.environ['LANG']
        config.winenv()
        self.assertEqual(os.getenv('LANG'), 'foobar')
        os.environ['LANG'] = lang
        config.eol = eol

