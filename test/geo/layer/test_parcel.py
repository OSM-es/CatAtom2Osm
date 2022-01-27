import logging
import mock
import unittest

from qgis.core import QgsFeature, QgsVectorLayer

from catatom2osm.app import QgsSingleton
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.parcel import ParcelLayer

qgs = QgsSingleton()
m_log = mock.MagicMock()
m_log.app_level = logging.INFO


class TestParcelLayer(unittest.TestCase):

    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    def setUp(self):
        fn = 'test/fixtures/parcel.gpkg|layername=parcel'
        self.parcel = ParcelLayer('MultiPolygon', 'parcel', 'memory')
        fixture = QgsVectorLayer(fn, 'parcel', 'ogr')
        self.assertTrue(fixture.isValid(), "Loading fixture")
        self.parcel.append(fixture)
        self.assertEqual(self.parcel.featureCount(), 186)
        fn = 'test/fixtures/cons.gpkg|layername=cons'
        self.building = ConsLayer(fn, 'cons', 'ogr')
        self.assertTrue(self.building.isValid(), "Loading fixture")

    def test_init(self):
        layer = ParcelLayer()
        self.assertEqual(layer.fields()[0].name(), 'localId')
        self.assertEqual(layer.fields()[1].name(), 'label')
        self.assertEqual(layer.rename['localId'], 'inspireId_localId')

    def test_not_empty(self):
        layer = ParcelLayer()
        self.assertEqual(len(layer.fields().toList()), 2)

    def test_delete_void_parcels(self):
        self.parcel.delete_void_parcels(self.building)
        self.assertEqual(self.parcel.featureCount(), 111)

    def test_create_missing_parcels(self):
        self.parcel.create_missing_parcels(self.building)
        self.assertEqual(self.parcel.featureCount(), 188)
        p = next(self.parcel.search("localId = '8642317CS5284S'"))
        self.assertEqual(len(Geometry.get_multipolygon(p)[0]), 1)

    def test_get_groups_with_context(self):
        self.parcel.create_missing_parcels(self.building)
        pa_groups, __, __ = self.parcel.get_groups_with_context(self.building)
        expected = [
            {48, 9, 10}, {14, 15}, {16, 17}, {18, 19, 20, 22, 23},
            {34, 35, 55}, {56, 36, 37}, {32, 33, 38, 39},
            {40, 41, 42, 43, 44, 45, 27, 24, 25, 26, 187, 28, 29, 30, 31},
            {11, 12, 46, 47}, {8, 49, 50, 7}, {51, 52, 5, 6}, {3, 4, 53, 54},
            {57, 58}, {64, 65, 66, 71, 59, 60, 61, 62, 63}, {81, 77, 78},
            {80, 79}, {84, 85}, {86, 87}, {91, 92}, {107, 99, 100}
        ]
        self.assertEqual(pa_groups, expected)

    def test_merge_by_adjacent_buildings(self):
        self.parcel.delete_void_parcels(self.building)
        self.parcel.create_missing_parcels(self.building)
        tasks = self.parcel.merge_by_adjacent_buildings(self.building)
        self.assertEqual(self.parcel.featureCount(), 55)
        pa_refs = [f['localId'] for f in self.parcel.getFeatures()]
        merged = []
        for bu in self.building.getFeatures():
            ref = self.building.get_id(bu)
            if ref not in pa_refs:
                merged.append(ref)
        self.assertEqual(len(merged), 58)
        self.assertTrue(all([tasks[ref] != ref for ref in merged]))
