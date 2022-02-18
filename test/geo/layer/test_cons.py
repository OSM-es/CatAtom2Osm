import logging
import unittest
from collections import Counter

import mock
from qgis.core import QgsExpression, QgsFeature, QgsFeatureRequest, QgsVectorLayer

from catatom2osm import osm
from catatom2osm.app import QgsSingleton
from catatom2osm.geo.aux import is_inside
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.address import AddressLayer
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.point import Point

qgs = QgsSingleton()
m_log = mock.MagicMock()
m_log.app_level = logging.INFO


class TestConsLayerSimple(unittest.TestCase):
    def test_is_building(self):
        self.assertTrue(ConsLayer.is_building({"localId": "foobar"}))
        self.assertFalse(ConsLayer.is_building({"localId": "foo_bar"}))

    def test_is_part(self):
        self.assertTrue(ConsLayer.is_part({"localId": "foo_part1"}))
        self.assertFalse(ConsLayer.is_part({"localId": "foo_PI.1"}))

    def test_is_pool(self):
        self.assertTrue(ConsLayer.is_pool({"localId": "foo_PI.1"}))
        self.assertFalse(ConsLayer.is_pool({"localId": "foo_part1"}))

    def test_get_id(self):
        buil = {"localId": "XXXXXX14XXXXXX"}
        part = {"localId": "XXXXXX14XXXXXX_part9"}
        pool = {"localId": "XXXXXX14XXXXXX_PI.99"}
        addr = {"localId": "99.999.9.9.XXXXXX14XXXXXX"}
        self.assertTrue(ConsLayer.get_id(part), buil["localId"])
        self.assertTrue(ConsLayer.get_id(pool), buil["localId"])
        self.assertTrue(ConsLayer.get_id(addr), buil["localId"])


class TestConsLayer(unittest.TestCase):
    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def setUp(self):
        fn = "test/fixtures/cons.shp"
        self.fixture = QgsVectorLayer(fn, "building", "ogr")
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        fn = "test_layer.shp"
        ConsLayer.create_shp(fn, self.fixture.crs())
        self.layer = ConsLayer(fn, "zoning", "ogr")
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.append(self.fixture, rename="")
        self.assertEqual(self.layer.featureCount(), self.fixture.featureCount())

    def tearDown(self):
        del self.layer
        ConsLayer.delete_shp("test_layer.shp")

    def test_merge_adjacent_features(self):
        parts = [p for p in self.layer.search("localId like '8840501CS5284S_part%%'")]
        geom = Geometry.merge_adjacent_features(parts)
        area = sum([p.geometry().area() for p in parts])
        self.assertEqual(100 * round(geom.area(), 2), 100 * round(area, 2))
        self.assertGreater(len(Geometry.get_multipolygon(geom)), 0)
        self.assertLess(len(Geometry.get_multipolygon(geom)), len(parts))

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_explode_multi_parts(self):
        mp0 = [
            f for f in self.layer.getFeatures() if len(Geometry.get_multipolygon(f)) > 1
        ]
        self.assertGreater(len(mp0), 0)
        address = AddressLayer()
        fn = "test/fixtures/address.gml"
        address_gml = QgsVectorLayer(fn, "address", "ogr")
        address.append(address_gml)
        refs = {ad["localId"].split(".")[-1] for ad in address.getFeatures()}
        mp1 = [
            f
            for f in self.layer.getFeatures()
            if f["localId"] in refs and len(Geometry.get_multipolygon(f)) > 1
        ]
        self.assertGreater(len(mp1), 0)
        self.layer.explode_multi_parts(address)
        mp2 = [
            f for f in self.layer.getFeatures() if len(Geometry.get_multipolygon(f)) > 1
        ]
        self.assertEqual(len(mp1), len(mp2))

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_append_building(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fn = "test/fixtures/building.gml"
        fixture = QgsVectorLayer(fn, "building", "ogr")
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = next(fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature["conditionOfConstruction"], new_fet["condition"])
        self.assertEqual(feature["localId"], new_fet["localId"])

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_append_buildingpart(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fn = "test/fixtures/buildingpart.gml"
        fixture = QgsVectorLayer(fn, "building", "ogr")
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = next(fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature["numberOfFloorsAboveGround"], new_fet["lev_above"])
        self.assertEqual(feature["localId"], new_fet["localId"])

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_append_othercons(self):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fn = "test/fixtures/othercons.gml"
        fixture = QgsVectorLayer(fn, "building", "ogr")
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = next(fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature["constructionNature"], new_fet["nature"])
        self.assertEqual(feature["localId"], new_fet["localId"])

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_append_cons(self):
        exp = QgsExpression("nature = 'openAirPool'")
        request = QgsFeatureRequest(exp)
        feat = next(self.layer.getFeatures(request))
        self.assertNotEqual(feat, None)
        layer = ConsLayer()
        layer.rename = {}
        layer.append(self.layer)
        feat = next(layer.getFeatures(request))
        self.assertNotEqual(feat, None)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_remove_parts_below_ground(self):
        to_clean = [f.id() for f in self.layer.search("lev_above=0 and lev_below>0")]
        self.assertGreater(len(to_clean), 0, "There are parts below ground")
        self.layer.remove_outside_parts()
        to_clean = [f.id() for f in self.layer.search("lev_above=0 and lev_below>0")]
        self.assertEqual(len(to_clean), 0, "There are not parts below ground")

    def test_index_of_parts(self):
        parts = self.layer.index_of_parts()
        p = {f.id(): f for f in self.layer.getFeatures() if self.layer.is_part(f)}
        self.assertEqual(sum(len(g) for g in list(parts.values())), len(p))
        for (localid, group) in list(parts.items()):
            for pa in group:
                self.assertTrue(localid, pa["localid"].split("_")[0])
                self.assertIn("_", pa["localid"])

    def test_index_of_building_and_parts(self):
        (buildings, parts) = self.layer.index_of_building_and_parts()
        b = [f for f in self.layer.getFeatures() if self.layer.is_building(f)]
        p = [f for f in self.layer.getFeatures() if self.layer.is_part(f)]
        self.assertEqual(sum(len(g) for g in list(buildings.values())), len(b))
        self.assertEqual(sum(len(g) for g in list(parts.values())), len(p))
        self.assertTrue(
            all(
                [
                    localid == bu["localid"]
                    for (localid, group) in list(buildings.items())
                    for bu in group
                ]
            )
        )
        self.assertTrue(
            all(
                [
                    localid == pa["localid"][0:14]
                    for (localid, group) in list(parts.items())
                    for pa in group
                ]
            )
        )

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_remove_outside_parts(self):
        refs = [
            "8742721CS5284S_part10",
            "8742721CS5284S_part5",
            "8742708CS5284S_part1",
            "8742707CS5284S_part2",
            "8742707CS5284S_part6",
        ]
        self.layer.remove_outside_parts()
        for feat in self.layer.getFeatures():
            self.assertNotIn(feat["localId"], refs)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_get_parts(self):
        self.layer.explode_multi_parts()
        parts = [p for p in self.layer.search("localId like '8840501CS5284S_part%%'")]
        for outline in self.layer.search("localId = '8840501CS5284S'"):
            parts_inside = [p for p in parts if is_inside(p, outline)]
            parts_for_level, max_level, min_level = self.layer.get_parts(outline, parts)
            max_levelc = max([p["lev_above"] for p in parts_inside])
            min_levelc = max([p["lev_below"] for p in parts_inside])
            self.assertEqual(
                len(parts_inside), sum([len(p) for p in list(parts_for_level.values())])
            )
            for part in parts_inside:
                self.assertIn(
                    part, parts_for_level[(part["lev_above"], part["lev_below"])]
                )
            self.assertEqual(max_level, max_levelc)
            self.assertEqual(min_level, min_levelc)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_merge_adjacent_parts(self, ref=None):
        if ref == None:
            self.layer.explode_multi_parts()
            ref = "8842323CS5284S"
        parts = [p for p in self.layer.search("localId like '%s_part%%'" % ref)]
        for outline in self.layer.search("localId = '%s'" % ref):
            cn, cng, ch, chg = self.layer.merge_adjacent_parts(outline, parts)
            parts_for_level, max_level, min_level = self.layer.get_parts(outline, parts)
            if len(parts_for_level) > 1:
                areap = 0
                for level, group in list(parts_for_level.items()):
                    geom = Geometry.merge_adjacent_features(group)
                    poly = Geometry.get_multipolygon(geom)
                    if len(poly) < len(group):
                        areap += geom.area()
                aream = sum([g.area() for g in list(chg.values())])
                self.assertEqual(100 * round(areap, 2), 100 * round(aream, 2))
                self.assertEqual(len(cn), 0)
            else:
                self.assertEqual(
                    set(cn),
                    set([p.id() for p in parts_for_level[max_level, min_level]]),
                )
            self.assertEqual(
                max([l[0] for l in list(parts_for_level.keys())]), max_level
            )
            self.assertEqual(
                max([l[1] for l in list(parts_for_level.keys())]), min_level
            )
            self.assertEqual(ch[outline.id()][6], max_level)
            self.assertEqual(ch[outline.id()][7], min_level)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_merge_building_parts(self):
        self.layer.remove_outside_parts()
        self.layer.merge_building_parts()
        for ref in self.layer.getFeatures():
            if self.layer.is_building(ref):
                self.test_merge_adjacent_parts(ref)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_add_topological_points(self):
        refs = [
            ("8842708CS5284S", Point(358821.08, 3124205.68), 0),
            ("8842708CS5284S_part1", Point(358821.08, 3124205.68), 0),
            ("8942328CS5284S", Point(358857.04, 3124248.6705), 1),
            ("8942328CS5284S_part3", Point(358857.04, 3124248.6705), 0),
        ]
        for ref in refs:
            building = next(self.layer.search("localId = '%s'" % ref[0]))
            poly = Geometry.get_multipolygon(building)
            self.assertNotIn(ref[1], poly[ref[2]][0])
        self.layer.topology()
        for ref in refs:
            building = next(self.layer.search("localId = '%s'" % ref[0]))
            poly = Geometry.get_multipolygon(building)
            self.assertIn(ref[1], poly[ref[2]][0])

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_delete_invalid_geometries(self):
        f1 = QgsFeature(self.layer.fields())
        g1 = Geometry.fromPolygonXY(
            [
                [
                    Point(358794.000, 3124330.000),
                    Point(358794.200, 3124329.800),
                    Point(358794.400, 3124330.000),
                    Point(358794.200, 3124500.000),
                    Point(358794.000, 3124330.000),
                ]
            ]
        )
        f1.setGeometry(g1)
        f2 = QgsFeature(self.layer.fields())
        g2 = Geometry.fromPolygonXY(
            [
                [
                    Point(358794.000, 3124330.000),
                    Point(358795.000, 3124331.000),
                    Point(358794.500, 3124500.000),
                    Point(358794.000, 3124330.000),
                ]
            ]
        )
        f2.setGeometry(g2)
        f3 = QgsFeature(self.layer.fields())
        g3 = Geometry.fromPolygonXY(
            [
                [
                    Point(358890.000, 3124329.000),
                    Point(358900.000, 3124329.000),
                    Point(358900.000, 3124501.000),
                    Point(358890.000, 3124501.000),
                    Point(358890.000, 3124330.000),
                ],
                [
                    Point(358894.000, 3124330.000),
                    Point(358895.000, 3124331.000),
                    Point(358894.500, 3124500.000),
                    Point(358894.000, 3124330.000),
                ],
            ]
        )
        f3.setGeometry(g3)
        f4 = QgsFeature(self.layer.fields())
        g4 = Geometry.fromPolygonXY(
            [
                [
                    Point(357400.00, 3124305.00),  # spike
                    Point(357405.00, 3124305.04),
                    Point(357404.99, 3124307.60),
                    Point(357405.00, 3124307.40),  # zig-zag
                    Point(357405.00, 3124313.00),  # spike
                    Point(357405.04, 3124310.00),
                    Point(357407.50, 3124311.00),
                    Point(357409.96, 3124310.00),
                    Point(357410.00, 3124313.00),  # spike
                    Point(357410.02, 3124306.00),
                    Point(357410.00, 3124305.00),
                    Point(357400.00, 3124305.00),
                ]
            ]
        )
        f4.setGeometry(g4)
        f5 = QgsFeature(self.layer.fields())
        g5 = Geometry.fromPolygonXY(
            [
                [
                    Point(357400.00, 3124305.00),
                    Point(357405.00, 3124305.04),
                    Point(357405.00, 3124310.00),
                    Point(357400.00, 3124310.00),
                    Point(357400.00, 3124305.00),
                ]
            ]
        )
        f5.setGeometry(g5)
        fc = self.layer.featureCount()
        self.layer.writer.addFeatures([f1, f2, f3, f4, f5])
        self.layer.delete_invalid_geometries()
        self.assertEqual(fc, self.layer.featureCount() - 3)
        request = QgsFeatureRequest().setFilterFid(self.layer.featureCount() - 3)
        f = next(self.layer.getFeatures(request))
        mp = Geometry.get_multipolygon(f)
        self.assertEqual(len(mp[0]), 1)
        request = QgsFeatureRequest().setFilterFid(self.layer.featureCount() - 2)
        f = next(self.layer.getFeatures(request))
        mp = Geometry.get_multipolygon(f)
        r = [
            (357410.00, 3124305.00),
            (357405.00, 3124305.00),
            (357405.00, 3124309.98),
            (357407.50, 3124311.00),
            (357410.01, 3124310.02),
            (357410.02, 3124306.00),
            (357410.00, 3124305.00),
        ]
        self.assertEqual(r, [(round(p.x(), 2), round(p.y(), 2)) for p in mp[0][0]])
        request = QgsFeatureRequest().setFilterFid(self.layer.featureCount() - 1)
        f = next(self.layer.getFeatures(request))
        mp = Geometry.get_multipolygon(f)
        r = [
            (357400.00, 3124305.00),
            (357400.00, 3124310.00),
            (357405.00, 3124310.00),
            (357405.00, 3124305.00),
            (357400.00, 3124305.00),
        ]
        self.assertEqual(r, [(round(p.x(), 2), round(p.y(), 2)) for p in mp[0][0]])

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_simplify1(self):
        refs = [
            ("8643326CS5284S", Point(358684.62, 3124377.54), True),
            ("8643326CS5284S", Point(358686.29, 3124376.11), True),
            ("8643324CS5284S", Point(358677.29, 3124366.64), False),
        ]
        self.layer.explode_multi_parts()
        self.layer.simplify()
        for ref in refs:
            building = next(self.layer.search("localId = '%s'" % ref[0]))
            self.assertEqual(
                ref[1] in Geometry.get_multipolygon(building)[0][0], ref[2]
            )

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.polygon.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_simplify2(self):
        layer = ConsLayer()
        fn = "test/fixtures/38023.buildingpart.gml"
        fixture1 = QgsVectorLayer(fn, "building", "ogr")
        self.assertTrue(fixture1.isValid(), "Loading fixture")
        layer.append(fixture1, rename="")
        self.assertEqual(layer.featureCount(), fixture1.featureCount())
        fn = "test/fixtures/38023.buildingpart.gml"
        fixture2 = QgsVectorLayer(fn, "buildingpart", "ogr")
        self.assertTrue(fixture2.isValid(), "Loading fixture")
        layer.append(fixture2, rename="")
        self.assertEqual(
            layer.featureCount(),
            fixture1.featureCount() + fixture2.featureCount(),
        )
        layer.remove_outside_parts()
        layer.explode_multi_parts()
        layer.topology()
        layer.simplify()
        for feat in layer.getFeatures():
            geom = feat.geometry()
            self.assertTrue(geom.isGeosValid(), feat["localId"])
        layer.merge_building_parts()

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_move_address(self):
        refs = {
            "38.012.10.10.8643403CS5284S": "Entrance",
            "38.012.10.11.8842304CS5284S": "Entrance",
            # '38.012.10.13.8842305CS5284S': 'Entrance',
            "38.012.10.14.8643404CS5284S": "corner",
            "38.012.10.14.8643406CS5284S": "Parcel",
            "38.012.10.2.8642321CS5284S": "Entrance",
            "38.012.15.73.8544911CS5284S": "remote",
        }
        self.layer.explode_multi_parts()
        address = AddressLayer()
        fn = "test/fixtures/address.gml"
        address_gml = QgsVectorLayer(fn, "address", "ogr")
        address.append(address_gml)
        self.assertEqual(address.featureCount(), 14)
        self.layer.move_address(address)
        self.assertEqual(address.featureCount(), 7)
        for ad in address.getFeatures():
            if ad["localId"] in list(refs.keys()):
                self.assertEqual(ad["spec"], refs[ad["localId"]])
                if ad["spec"] == "Entrance":
                    refcat = ad["localId"].split(".")[-1]
                    building = next(self.layer.search("localId = '%s'" % refcat))
                    self.assertTrue(ad.geometry().touches(building.geometry()))
        self.layer.move_address(address)
        self.assertEqual(address.featureCount(), 6)

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_validate(self):
        self.layer.merge_building_parts()
        max_level = {}
        min_level = {}
        self.layer.validate(max_level, min_level)
        refs = ["7239208CS5273N", "38012A00400007"]
        for (l, v) in list({1: 126, 2: 114, 3: 67, 4: 16, 5: 1}.items()):
            self.assertEqual(Counter(list(max_level.values()))[l], v)
        for (l, v) in list({1: 68, 2: 2}.items()):
            self.assertEqual(Counter(list(min_level.values()))[l], v)
        for ref in refs:
            exp = QgsExpression("localId = '%s'" % ref)
            request = QgsFeatureRequest(exp)
            feat = next(self.layer.getFeatures(request))
            self.assertNotEqual(feat["fixme"], "")

    def test_to_osm(self):
        data = self.layer.to_osm(upload="always")
        self.assertEqual(data.upload, "always")
        ways = 0
        rels = 0
        c = Counter()
        for feat in self.layer.getFeatures():
            p = Geometry.get_multipolygon(feat)
            ways += sum([len(s) for s in p])
            rels += 1 if len(p) + len(p[0]) > 2 else 0
        self.assertEqual(ways, len(data.ways))
        self.assertEqual(rels, len(data.relations))

    @mock.patch("catatom2osm.geo.layer.base.log", m_log)
    @mock.patch("catatom2osm.geo.layer.cons.log", m_log)
    @mock.patch("catatom2osm.geo.layer.base.tqdm", mock.MagicMock())
    def test_conflate(self):
        self.layer.reproject()
        d = osm.Osm()
        d.Way(
            (
                (-16.44211325828, 28.23715394977),
                (-16.44208978895, 28.23714124855),
                (-16.44209884141, 28.23712884271),
                (-16.44212197546, 28.23714361157),
                (-16.44211325828, 28.23715394977),
            ),
            dict(building="yes", ref="1"),
        )
        d.Way(
            (
                (-16.44016295806, 28.23657619128),
                (-16.43985450402, 28.23641077902),
                (-16.43991753593, 28.23632689127),
                (-16.44020855561, 28.23648403305),
                (-16.44016295806, 28.23657619128),
            ),
            dict(building="yes", ref="2"),
        )
        d.Way(
            (
                (-16.44051231511, 28.23655551417),
                (-16.44042112, 28.23650529975),
                (-16.4405699826, 28.23631153095),
                (-16.44065782495, 28.23635288407),
                (-16.44051231511, 28.23655551417),
            ),
            dict(building="yes", ref="3"),
        )
        self.assertEqual(len(d.ways), 3)
        self.layer.conflate(d, delete=False)
        self.assertEqual(len(d.ways), 3)
        for el in d.ways:
            self.assertEqual("conflict" in el.tags, el.tags["ref"] == "3")
        d.Way(
            (
                (-16.44038491018, 28.23645095),
                (-16.44029706784, 28.23640132629),
                (-16.44042514332, 28.23624713819),
                (-16.44049689241, 28.23629558045),
                (-16.44038491018, 28.23645095),
            ),
            dict(building="yes", ref="4"),
        )
        d.Way(
            (
                (-16.44019514591, 28.23634461522),
                (-16.44002616674, 28.23625009376),
                (-16.44011199743, 28.23611540052),
                (-16.44027829438, 28.23619810692),
            ),
            dict(building="yes", ref="5"),
        )
        d.Way(
            (
                (-16.43993497163, 28.23591926797),
                (-16.43972575933, 28.23580584175),
                (-16.4398062256, 28.23610122228),
                (-16.43959701329, 28.23598543321),
                (-16.43993497163, 28.23591926797),
            ),
            dict(building="yes", ref="6"),
        )
        d.Way(
            (
                (-16.4386775, 28.2360472),
                (-16.4386158, 28.2363235),
                (-16.4384536, 28.2362954),
                (-16.4385153, 28.2360191),
                (-16.4386775, 28.2360472),
            ),
            dict(building="yes", ref="7"),
        )
        d.Way(
            (
                (-16.4386049, 28.2357006),
                (-16.4385316, 28.2356401),
                (-16.4385093, 28.2356419),
                (-16.4384993, 28.2357054),
                (-16.4386049, 28.2357006),
            ),
            dict(building="yes", ref="8"),
        )
        w0 = d.Way(
            (
                (-16.4409784, 28.2365733),
                (-16.4409231, 28.236542),
                (-16.4409179, 28.2365154),
                (-16.4409268, 28.236504),
                (-16.4408588, 28.236465),
            )
        )
        w1 = d.Way(((-16.4406755, 28.236688), (-16.4408332, 28.2367735)))
        w2 = d.Way(
            (
                (-16.4408332, 28.2367735),
                (-16.4408943, 28.2366893),
                (-16.4409395, 28.2367147),
                (-16.4409818, 28.2366563),
                (-16.4409366, 28.2366308),
                (-16.4409784, 28.2365733),
            )
        )
        w3 = d.Way(
            (
                (-16.4408588, 28.236465),
                (-16.4408086, 28.2365319),
                (-16.4407037, 28.2364709),
                (-16.4406669, 28.2365102),
                (-16.4406513, 28.2365338),
                (-16.440639, 28.2365663),
                (-16.4407394, 28.2366223),
                (-16.4407188, 28.2366474),
                (-16.440707, 28.2366405),
                (-16.4406755, 28.236688),
            )
        )
        w4 = d.Way(
            (
                (-16.440072, 28.236560),
                (-16.439966, 28.236505),
                (-16.439888, 28.236605),
                (-16.4399860, 28.236666),
                (-16.440072, 28.236560),
            )
        )
        w5 = d.Way(
            (
                (-16.439965, 28.236703),
                (-16.439861, 28.236642),
                (-16.439805, 28.236733),
                (-16.439903, 28.236790),
                (-16.439965, 28.236703),
            )
        )
        r1 = d.Relation(tags=dict(building="yes", ref="9"))
        r1.append(w0, "outer")
        r1.append(w1, "outer")
        r1.append(w2, "outer")
        r1.append(w3, "outer")
        r2 = d.Relation(tags=dict(building="yes", ref="10"))
        r2.append(w4, "outer")
        r2.append(w5, "outer")
        self.assertEqual(len(d.ways), 14)
        self.assertEqual(len(d.relations), 2)
        self.layer.conflate(d)
        self.assertEqual(len(d.ways), 12)
        self.assertEqual(len(d.relations), 2)
        self.assertEqual(
            {e.tags["ref"] for e in d.ways if "ref" in e.tags},
            {"3", "4", "5", "6", "7", "8"},
        )
