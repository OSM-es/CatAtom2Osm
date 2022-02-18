import logging
import unittest

import mock
from qgis.core import QgsFeature, QgsFeatureRequest, QgsVectorLayer

from catatom2osm.app import QgsSingleton
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.polygon import PolygonLayer
from catatom2osm.geo.point import Point

qgs = QgsSingleton()
m_log = mock.MagicMock()
m_log.app_level = logging.INFO

class TestPolygonLayer(unittest.TestCase):

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def setUp(self):
        fn = 'test/fixtures/cons.shp'
        self.fixture = QgsVectorLayer(fn, 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), f"Loading {fn}")
        fn = 'test_layer.shp'
        PolygonLayer.create_shp(fn, self.fixture.crs())
        self.layer = PolygonLayer(fn, 'building', 'ogr')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.append(self.fixture, rename='')
        self.assertEqual(self.layer.featureCount(), self.fixture.featureCount())

    def tearDown(self):
        del self.layer
        PolygonLayer.delete_shp('test_layer.shp')

    @mock.patch('catatom2osm.geo.layer.polygon.log', m_log)
    def test_get_area(self):
        area = self.layer.get_area()
        self.assertEqual(round(area, 1), 1140234.8)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_explode_multi_parts(self):
        multiparts = [f for f in self.layer.getFeatures()
            if len(Geometry.get_multipolygon(f)) > 1]
        self.assertGreater(len(multiparts), 0, "There are multipart features")
        features_before = self.layer.featureCount()
        request = QgsFeatureRequest()
        request.setFilterFid(multiparts[0].id())
        nparts = len(Geometry.get_multipolygon(multiparts[0]))
        self.layer.explode_multi_parts(request)
        self.assertEqual(features_before + nparts - 1, self.layer.featureCount())
        nparts = sum([len(Geometry.get_multipolygon(f)) for f in multiparts])
        self.assertGreater(nparts, len(multiparts), "With more than one part")
        self.assertTrue(nparts > 1, "Find a multipart feature")
        self.layer.explode_multi_parts()
        m = "After exploding there must be more features than before"
        self.assertGreater(self.layer.featureCount(), features_before, m)
        m = "Number of features before plus number of parts minus multiparts " \
            "equals actual number of features"
        self.assertEqual(features_before + nparts - len(multiparts),
            self.layer.featureCount(), m)
        m = "Parts must be single polygons"
        self.assertTrue(all([len(Geometry.get_multipolygon(f)) == 1
            for f in self.layer.getFeatures()]), m)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    def test_get_parents_per_vertex_and_geometries(self):
        (parents_per_vertex, geometries) = self.layer.get_parents_per_vertex_and_geometries()
        self.assertEqual(len(geometries), self.layer.featureCount())
        self.assertTrue(all([Geometry.get_multipolygon(geometries[f.id()]) == \
            Geometry.get_multipolygon(f)
                for f in self.layer.getFeatures()]))
        self.assertGreater(len(parents_per_vertex), 0)
        self.assertTrue(all([
            Geometry.fromPointXY(Point(vertex)).intersects(geometries[fid])
            for (vertex, fids) in list(parents_per_vertex.items())
            for fid in fids
        ]))

    def get_duplicates(self):
        """
        Returns a dict of duplicated vertices for each coordinate.
        Two vertices are duplicated if they are nearest than dup_thr.
        """
        vertices = BaseLayer('Point', 'vertices', 'memory')
        for feature in self.layer.getFeatures():
            for point in self.layer.get_vertices_list(feature):
                feat = QgsFeature(QgsFields())
                geom = Geometry.fromPointXY(point)
                feat.setGeometry(geom)
                vertices.dataProvider().addFeatures([feat])
        dup_thr = self.layer.dup_thr
        vertex_by_fid = {f.id(): f.geometry().asPoint() for f in vertices.getFeatures() }
        index = vertices.get_index()
        duplicates = defaultdict(set)
        for vertex in vertices.getFeatures():
            point = Point(vertex.geometry().asPoint())
            area_of_candidates = point.boundingBox(dup_thr)
            fids = index.intersects(area_of_candidates)
            fids.remove(vertex.id())
            for fid in fids:
                dup = vertex_by_fid[fid]
                dist = point.sqrDist(dup)
                if dist > 0 and dist < dup_thr**2:
                    duplicates[point].add(dup)
        del vertices
        return duplicates

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_difference(self):
        layer1 = PolygonLayer('Polygon', 'test1', 'memory')
        layer2 = PolygonLayer('Polygon', 'test2', 'memory')
        g1 = Geometry.fromPolygonXY([[Point(10,10),
            Point(20,10), Point(20,20), Point(10,20), Point(10,10)
        ]])
        g2 = Geometry.fromPolygonXY([[Point(30,10),
            Point(40,10), Point(40,20), Point(30,20), Point(30,10)
        ]])
        h1 = Geometry.fromPolygonXY([[Point(14,14),
            Point(16,14), Point(16,16), Point(14,16), Point(14,14)
        ]])
        h2 = Geometry.fromPolygonXY([[Point(20,10),
            Point(30,10), Point(30,20), Point(20,20), Point(20,10)
        ]])
        h3 = Geometry.fromPolygonXY([[Point(38,10),
            Point(42,10), Point(42,20), Point(38,20), Point(38,10)
        ]])
        h4 = Geometry.fromPolygonXY([[Point(30,30),
            Point(40,30), Point(40,40), Point(40,30), Point(30,30)
        ]])
        r1 = g1.difference(h1)
        r2 = g2.difference(h3)
        layer1.writer.addFeatures([QgsFeature() for i in range(2)])
        layer1.writer.changeGeometryValues({1: g1, 2: g2})
        layer2.writer.addFeatures([QgsFeature() for i in range(4)])
        layer2.writer.changeGeometryValues({1: h1, 2: h2, 3: h3, 4: h4})
        layer1.difference(layer2)
        self.assertEqual(layer1.featureCount(), 2)
        request = QgsFeatureRequest().setFilterFid(1)
        f1 = next(layer1.getFeatures(request))
        request = QgsFeatureRequest().setFilterFid(2)
        f2 = next(layer1.getFeatures(request))
        self.assertEqual(f1.geometry().difference(r1).area(), 0)
        self.assertEqual(f2.geometry().difference(r2).area(), 0)
