import io
import logging
import unittest

import mock
from qgis.core import QgsFeature, QgsVectorLayer

from catatom2osm import osmxml
from catatom2osm.app import QgsSingleton
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.parcel import ParcelLayer

qgs = QgsSingleton()
m_log = mock.MagicMock()
m_log.app_level = logging.INFO


class TestParcelLayer(unittest.TestCase):
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    def setUp(self):
        fn = "test/fixtures/parcel.gpkg|layername=parcel"
        self.parcel = ParcelLayer("38012")
        fixture = QgsVectorLayer(fn, "parcel", "ogr")
        self.assertTrue(fixture.isValid(), "Loading fixture")
        self.parcel.append(fixture)
        self.assertEqual(self.parcel.featureCount(), 186)
        fn = "test/fixtures/cons.gpkg|layername=cons"
        fixture2 = QgsVectorLayer(fn, "cons", "ogr")
        self.building = ConsLayer("MultiPolygon", "cons", "memory")
        self.building.append(fixture2)
        self.assertTrue(self.building.isValid(), "Loading fixture")

    def test_init(self):
        layer = ParcelLayer("38012")
        self.assertEqual(layer.fields()[0].name(), "localId")
        self.assertEqual(layer.fields()[1].name(), "parts")
        self.assertEqual(layer.rename["localId"], "inspireId_localId")

    def test_not_empty(self):
        layer = ParcelLayer("38012")
        self.assertGreater(len(layer.fields().toList()), 0)

    def test_delete_void_parcels(self):
        self.parcel.delete_void_parcels(self.building)
        self.assertEqual(self.parcel.featureCount(), 110)

    def test_create_missing_parcels(self):
        self.parcel.create_missing_parcels(self.building)
        self.assertEqual(self.parcel.featureCount(), 188)
        p = next(self.parcel.search("localId = '8642317CS5284S'"))
        self.assertEqual(len(Geometry.get_multipolygon(p)[0]), 1)

    def test_get_groups_by_adjacent_buildings(self):
        self.parcel.create_missing_parcels(self.building)
        pa_groups, pa_refs, __ = self.parcel.get_groups_by_adjacent_buildings(
            self.building
        )
        self.assertEqual(len(pa_groups), 21)
        self.assertEqual(sum([len(gr) for gr in pa_groups]), 85)

    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    def test_merge_by_adjacent_buildings(self):
        self.building.remove_outside_parts()
        self.building.explode_multi_parts()
        self.building.clean()
        self.parcel.delete_void_parcels(self.building)
        self.parcel.create_missing_parcels(self.building)
        self.parcel.count_parts(self.building)
        pca = sum([f["parts"] for f in self.parcel.getFeatures()])
        la = self.parcel.featureCount()
        tasks = self.parcel.merge_by_adjacent_buildings(self.building)
        pcd = sum([f["parts"] for f in self.parcel.getFeatures()])
        ld = self.parcel.featureCount()
        cl = len([k for k, v in tasks.items() if k != v])
        self.assertEqual(ld, la - cl)
        self.assertEqual(pca, pcd)
        pa_refs = [f["localId"] for f in self.parcel.getFeatures()]
        expected = [
            "001000300CS52D",
            "001000400CS52D",
            "8641608CS5284S",
            "8641612CS5284S",
            "8641613CS5284S",
            "8641616CS5284S",
            "8641620CS5284S",
            "8641621CS5284S",
            "8641632CS5284S",
            "8641636CS5284S",
            "8641638CS5284S",
            "8641649CS5284S",
            "8641653CS5284S",
            "8641658CS5284S",
            "8641660CS5284S",
            "8642302CS5284S",
            "8642310CS5284S",
            "8642312CS5284S",
            "8642313CS5284S",
            "8642314CS5284S",
            "8642317CS5284S",
            "8642321CS5284S",
            "8642325CS5484N",
            "8642701CS5284S",
            "8742701CS5284S",
            "8742707CS5284S",
            "8742711CS5284S",
            "8742721CS5284S",
            "8839301CS5283N",
            "8840501CS5284S",
            "8841602CS5284S",
            "8841603CS5284S",
            "8844121CS5284S",
            "8940301CS5284S",
            "8940302CS5284S",
            "8940305CS5284S",
            "8940306CS5284S",
            "8940307CS5284S",
            "8940309CS5284S",
            "8941505CS5284S",
            "9041703CS5294S",
            "9041704CS5294S",
            "9041705CS5294S",
            "9041716CS5294S",
            "9041719CS5294S",
            "9042401CS5294S",
            "9042402CS5294S",
            "9042404CS5294S",
        ]
        self.assertEqual(pa_refs, expected)
        f = next(self.parcel.search("localId = '8840501CS5284S'"))
        self.assertEqual(f["parts"], 11)
        merged = []
        for bu in self.building.getFeatures():
            if self.building.is_building(bu):
                ref = self.building.get_id(bu)
                if ref not in pa_refs:
                    merged.append(ref)
        self.assertEqual(len(merged), 71)
        self.assertTrue(all([tasks[ref] != ref for ref in merged]))

    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    def test_count_parts(self):
        self.building.remove_outside_parts()
        self.building.explode_multi_parts()
        self.building.clean()
        self.parcel.delete_void_parcels(self.building)
        self.parcel.create_missing_parcels(self.building)
        parts_count = self.parcel.count_parts(self.building)
        self.assertEqual(sum(parts_count.values()), 324)
        self.assertEqual(len(parts_count), self.parcel.featureCount())
        f = next(self.parcel.search("localId = '8840501CS5284S'"))
        self.assertEqual(f["parts"], 7)
        self.assertEqual(parts_count["8840501CS5284S"], 7)
        f = next(self.parcel.search("localId = '8840502CS5284S'"))
        self.assertEqual(f["parts"], 4)
        self.assertEqual(parts_count["8840502CS5284S"], 4)

    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    def test_get_groups_by_parts_count(self):
        self.building.remove_outside_parts()
        self.building.explode_multi_parts()
        self.building.clean()
        self.parcel.delete_void_parcels(self.building)
        self.parcel.create_missing_parcels(self.building)
        self.parcel.count_parts(self.building)
        self.parcel.merge_by_adjacent_buildings(self.building)
        features = {pa.id(): pa for pa in self.parcel.getFeatures()}
        (
            pa_groups,
            pa_refs,
            geometries,
            parts_count,
        ) = self.parcel.get_groups_by_parts_count(10, 100)
        self.assertEqual(len(parts_count), 48)
        self.assertEqual(len(pa_groups), 18)
        self.assertTrue(
            all(
                [
                    sum([parts_count[pa_refs[fid]] for fid in group]) <= 10
                    for group in pa_groups
                ]
            )
        )
        label_count = set(
            [
                len(set([self.parcel.get_zone(features[fid]) for fid in group]))
                for group in pa_groups
            ]
        )
        self.assertEqual(label_count, {1})

    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    def test_merge_by_parts_count(self):
        self.building.remove_outside_parts()
        self.building.explode_multi_parts()
        self.building.clean()
        self.parcel.delete_void_parcels(self.building)
        self.parcel.create_missing_parcels(self.building)
        self.parcel.merge_by_adjacent_buildings(self.building)
        pca = sum([f["parts"] for f in self.parcel.getFeatures()])
        la = self.parcel.featureCount()
        tasks = self.parcel.merge_by_parts_count(20, 30)
        pcd = sum([f["parts"] for f in self.parcel.getFeatures()])
        ld = self.parcel.featureCount()
        cl = len([k for k, v in tasks.items() if k != v])
        self.assertEqual(ld, la - cl)
        self.assertEqual(pca, pcd)
