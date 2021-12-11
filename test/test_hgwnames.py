# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from builtins import str
import unittest
import mock
import os
os.environ['LANGUAGE'] = 'C'

from catatom2osm import hgwnames


class TestHgwnames(unittest.TestCase):

    def setUp(self):
        self.temp_fuzz = hgwnames.fuzz
        self.ds = [
            {'id':1, 'n':'Foobar'}, 
            {'id':2, 'n':'Foo bar'}, 
            {'id':3, 'n':'Footaz'}
        ]
        self.fn = lambda x:x['n']
        self.choices = ['Foobar', 'Foo bar', 'Footaz']
        self.ds2 = [
            {'id':1, 'n':"Móstoles"}, 
            {'id':2, 'n':'Las Rozas de Madrid'},
            {'id':3, 'n':'Rivas-Vaciamadrid'},
            {'id':4, 'n':'Madrid'}]
        
    def test_normalize(self):
        self.assertEqual(hgwnames.normalize('  ABCD  '), 'abcd')

    def test_parse(self):
        names = {
            "   CL  FOO BAR  TAZ  ": "Calle Foo Bar Taz",
            "AV DE ESPAÑA": "Avenida de España",
            "CJ GATA (DE LA)": "Calleja/Callejón Gata (de la)",
            "CR CUMBRE,DE LA": "Carretera/Carrera Cumbre, de la",
            "CL HILARIO (ERAS LAS)": "Calle Hilario (Eras las)",
            "CL BASTIO D'EN SANOGUERA": "Calle Bastio d'en Sanoguera",
            "CL BANC DE L'OLI": "Calle Banc de l'Oli",
            "DS ARANJASSA,S'": "",
            "CL AIGUA DOLÇA (L')": "Calle Aigua Dolça (l')",
            "CL RUL·LAN": "Calle Rul·lan",
            "CL FONTE'L PILO": "Calle Fonte'l Pilo",
            "CL TRENET D'ALCOI": "Calle Trenet d'Alcoi",
            "CL SANT MARCEL.LI": "Calle Sant Marcel·li",
            "CL O'DONNELL": "Calle O'Donnell",
            "XX FooBar": "Xx Foobar"
        }
        for (inp, out) in list(names.items()):
            self.assertEqual(hgwnames.parse(inp), out)

    def test_fuzzy_match(self):
        self.assertEqual(hgwnames.match('FOOB', self.choices), 'Foobar')
        self.assertEqual(hgwnames.match('CL FRANCIA', self.choices), 'Calle Francia')

    @mock.patch('catatom2osm.hgwnames.fuzz', None)
    def test_nonfyzzy_match(self):
        self.assertEqual(hgwnames.match('CL FOOBAR', self.choices), 'Calle Foobar')

    def test_fuzzy_dsmatch(self):
        self.assertEqual(hgwnames.dsmatch('FOOB', self.ds, self.fn)['id'], 1)
        self.assertEqual(hgwnames.dsmatch('MADRID', self.ds2, self.fn)['id'], 4)
        self.assertEqual(hgwnames.dsmatch('MADRID', self.ds2, self.fn)['n'], 'Madrid')

    @mock.patch('catatom2osm.hgwnames.fuzz', None)
    def test_nonfuzzy_match(self):
        self.assertEqual(hgwnames.dsmatch('FOOBAR', self.ds, self.fn)['id'], 1)
        self.assertEqual(hgwnames.dsmatch('FOO', self.ds, self.fn), None)

    def tearDown(self):
        hgwnames.fuzz = self.temp_fuzz
