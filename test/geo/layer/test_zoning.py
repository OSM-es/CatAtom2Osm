import logging
import mock
import unittest
from collections import Counter

from qgis.core import QgsFeature, QgsVectorLayer

from catatom2osm.app import QgsSingleton
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.point import Point
from catatom2osm.geo.layer.base import BaseLayer
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.zoning import ZoningLayer

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
        self.ulayer.append(self.fixture, 'M')
        self.rlayer.append(self.fixture, 'P')
        self.assertGreater(
            self.ulayer.featureCount() + self.rlayer.featureCount(),
            self.fixture.featureCount()
        )
        for f in self.ulayer.getFeatures():
            self.assertTrue(self.ulayer.check_zone(f, level='M'))
        for f in self.rlayer.getFeatures():
            self.assertTrue(self.rlayer.check_zone(f, level='P'))

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_is_inside_full(self):
        self.ulayer.append(self.fixture, 'M')
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
        self.ulayer.append(self.fixture, 'M')
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
        self.ulayer.append(self.fixture, 'M')
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
        self.ulayer.append(self.fixture, 'M')
        (groups, geometries) = self.ulayer.get_adjacents_and_geometries()
        self.assertTrue(all([len(g) > 1 for g in groups]))
        for group in groups:
            for other in groups:
                if group != other:
                    self.assertTrue(all(p not in other for p in group))

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_set_tasks(self):
        self.ulayer.append(self.fixture, 'M')
        self.rlayer.append(self.fixture, 'P')
        self.ulayer.set_tasks('12345')
        labels = {int(f['label']) for f in self.ulayer.getFeatures()}
        self.assertEqual(max(labels), 92409)
        self.assertEqual(min(labels), 2003)
        self.assertEqual(next(self.ulayer.getFeatures())['zipcode'], '12345')
        self.rlayer.set_tasks('12345')
        labels = {int(f['label']) for f in self.rlayer.getFeatures()}
        self.assertEqual(max(labels), len(labels))
        self.assertEqual(min(labels), 1)
        self.assertEqual(next(self.rlayer.getFeatures())['zipcode'], '12345')

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_get_labels(self):
        self.ulayer.append(self.fixture, 'M')
        self.rlayer.append(self.fixture, 'P')
        test = Counter({
             '86416': 56, '84428': 21, '88423': 18, '86423': 18,
             '89423': 17, '86439': 17, '86417': 17, '90417': 12,
             '86464': 11, '88427': 9, '86435': 9, '85426': 9,
             '85449': 9, '87427': 9, '88429': 8, '89403': 8, '013': 7,
             '90425': 7, '91441': 7, '86434': 5, '83424': 5, '004': 4,
             '87425': 5, '87459': 4, '86448': 4, '83429': 4,
             '86433': 3, '88416': 3, '90424': 3, '85439': 3,
             '88405': 2, '005': 2, '85411': 2, '86459': 1, '88428': 1,
             '82426': 1, '83428': 1, '87432': 1, '86449': 1,
             '90429': 1, '86441': 1, '86427': 1, '89415': 1,
             '89414': 1, '88393': 1
        })
        fn = 'test/fixtures/cons.shp'
        source = ConsLayer(fn, 'building', 'ogr')
        building = BaseLayer('multipolygon', 'building', providerLib='memory')
        part = BaseLayer('multipolygon', 'part', providerLib='memory')
        building.append(source, query=lambda f, kwargs: source.is_building(f))
        part.append(source, query=lambda f, kwargs: source.is_part(f))
        self.ulayer.get_labels(source, building)
        self.rlayer.get_labels(source, building)
        self.ulayer.get_labels(source, part)
        self.rlayer.get_labels(source, part)
        self.assertFalse('000902900CS52D_part1' in source.labels)
        labels = Counter(source.labels.values())
        self.assertEqual(labels, test)

    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def do_test_split(self, split):
        splitted = [
            '001', '83462', '83462', '83468', '83469', '84486', '84499',
            '85461', '85462', '85463', '85490', '86464', '87483',
        ]
        self.ulayer.append(self.fixture, 'M')
        self.rlayer.append(self.fixture, 'P')
        self.ulayer.remove_outside_features(split, ['001'])
        self.assertEqual(self.ulayer.featureCount() + 1, len(splitted))
        for feat in self.ulayer.getFeatures():
            self.assertIn(feat['label'], splitted)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    def test_remove_outside_features1(self):
        """Splits using a polygon geojson created with QGIS"""
        split = BaseLayer('test/fixtures/split1.geojson', 'splitzoning', 'ogr')
        self.do_test_split(split)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    def test_remove_outside_features2(self):
        """Splits using a multipolygon geojson created with QGIS"""
        split = BaseLayer('test/fixtures/split2.geojson', 'splitzoning', 'ogr')
        self.do_test_split(split)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    def test_remove_outside_features3(self):
        """
        Splits using a polygon geojson with different CRS created with JOSM.
        Manually edited to change MultiString to Polygon
        """
        split = BaseLayer('test/fixtures/split3.geojson', 'splitzoning', 'ogr')
        self.do_test_split(split)
