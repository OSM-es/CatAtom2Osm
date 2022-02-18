import logging
import unittest
from collections import Counter

import mock
from qgis.core import QgsFeature, QgsVectorLayer

from catatom2osm.app import QgsSingleton
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.base import BaseLayer
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.zoning import ZoningLayer
from catatom2osm.geo.point import Point

qgs = QgsSingleton()
m_log = mock.MagicMock()
m_log.app_level = logging.INFO


class TestZoningLayer(unittest.TestCase):

    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def setUp(self):
        fn = 'test/fixtures/zoning.gml'
        self.fixture = QgsVectorLayer(fn, 'zoning', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        fn = 'urban_zoning.shp'
        ZoningLayer.create_shp(fn, self.fixture.crs())
        self.ulayer = ZoningLayer(fn, 'urbanzoning', 'ogr')
        self.assertTrue(self.ulayer.isValid(), "Init QGIS")
        fn = 'rustic_zoning.shp'
        ZoningLayer.create_shp(fn, self.fixture.crs())
        self.rlayer = ZoningLayer(fn, 'rusticzoning', 'ogr')
        self.assertTrue(self.rlayer.isValid(), "Init QGIS")

    def tearDown(self):
        del self.ulayer
        ZoningLayer.delete_shp('urban_zoning.shp')
        del self.rlayer
        ZoningLayer.delete_shp('rustic_zoning.shp')

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_append(self):
        bad_geoms = lambda l: [
            f for f in l.getFeatures() if not f.geometry().isGeosValid()
        ]
        self.assertGreater(len(bad_geoms(self.fixture)), 0)
        self.ulayer.append(self.fixture, level='M')
        self.rlayer.append(self.fixture, level='P')
        for f in self.ulayer.getFeatures():
            self.assertTrue(self.ulayer.check_zone(f, level='M'))
        for f in self.rlayer.getFeatures():
            self.assertTrue(self.rlayer.check_zone(f, level='P'))
        self.assertEqual(len(bad_geoms(self.ulayer)), 0)
        self.assertEqual(len(bad_geoms(self.rlayer)), 0)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_is_inside_full(self):
        self.ulayer.append(self.fixture, level='M')
        zone = Geometry.fromPolygonXY([[
            Point(357275.888, 3123959.765),
            Point(357276.418, 3123950.625),
            Point(357286.220, 3123957.911),
            Point(357275.888, 3123959.765),
        ]])
        feat = QgsFeature(self.ulayer.fields())
        feat.setGeometry(zone)
        self.assertTrue(self.ulayer.is_inside(feat))

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_is_inside_part(self):
        self.ulayer.append(self.fixture, level='M')
        feat = QgsFeature(self.ulayer.fields())
        zone = Geometry.fromPolygonXY([[
            Point(357270.987, 3123924.266),
            Point(357282.643, 3123936.187),
            Point(357283.703, 3123920.822),
            Point(357270.987, 3123924.266),
        ]])
        feat.setGeometry(zone)
        self.assertTrue(self.ulayer.is_inside(feat))

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_is_inside_false(self):
        self.ulayer.append(self.fixture, level='M')
        feat = QgsFeature(self.ulayer.fields())
        zone = Geometry.fromPolygonXY([[
            Point(357228.335, 3123901.881),
            Point(357231.779, 3123922.677),
            Point(357245.555, 3123897.377),
            Point(357228.335, 3123901.881),
        ]])
        feat.setGeometry(zone)
        self.assertFalse(self.ulayer.is_inside(feat))

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_get_adjacents_and_geometries(self):
        self.ulayer.append(self.fixture, level='M')
        (groups, geometries) = self.ulayer.get_adjacents_and_geometries()
        self.assertTrue(all([len(g) > 1 for g in groups]))
        for group in groups:
            for other in groups:
                if group != other:
                    self.assertTrue(all(p not in other for p in group))

