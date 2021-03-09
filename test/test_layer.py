# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from builtins import next, range, str, zip
import unittest
import mock
import os
import random
import six
from collections import Counter
import logging
logging.disable(logging.WARNING)

import gdal
from qgis.core import *
from qgiscompat import *

os.environ['LANGUAGE'] = 'C'
import setup
import osm
from layer import *
from catatom2osm import QgsSingleton
qgs = QgsSingleton()


class TestPoint(unittest.TestCase):

    def test_init(self):
        p = Point(1, 2)
        q = Point(p)
        r = Point((1,2))
        self.assertEqual(q.x(), r.x())
        self.assertEqual(q.y(), r.y())

    def test_boundigBox(self):
        radius = random.uniform(0, 100)
        point = Point(random.uniform(0, 100), random.uniform(0, 100))
        r = point.boundingBox(radius)
        self.assertEqual(round(r.center().x()*100), round(point.x()*100))
        self.assertEqual(round(r.center().y()*100), round(point.y()*100))
        self.assertEqual(round(r.width()*100), round(radius*200))
        self.assertEqual(round(r.height()*100), round(radius*200))

    def test_get_corner_context(self):
        square = Geometry.fromPolygonXY([[
            Point(0, 0),
            Point(50, 0.6), # dist > 0.5, angle < 5
            Point(100, 0),
            Point(105, 50), # dist > 0.5, angle > 5
            Point(100, 100),
            Point(2, 100.3), #dist < 0.5, angle > 5
            Point(0, 100),
            Point(0.3, 50), #dist < 0.5, angle < 5
            Point(0, 1),
            Point(-50, 0), # acute
            Point(0, 0)
        ]])
        acute_thr = 10
        straight_thr = 5
        cath_thr = 0.5
        (a, is_acute, is_corner, c) = Point(50, 0.4).get_corner_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertFalse(is_acute)
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(105, 51).get_corner_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertTrue(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(5.1, 100).get_corner_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(0.4, 50).get_corner_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(-51, 0).get_corner_context(square,
            acute_thr, straight_thr, cath_thr)
        self.assertTrue(is_acute)

    def test_get_spike_context(self):
        square = Geometry.fromPolygonXY([[
            Point(0, 50), # spike angle_v < 5 angle_a > 5 c < 0.5
            Point(50, 50.4),
            Point(49.9, 76),
            Point(50, 74), # zig-zag
            Point(50, 130),
            Point(50.4, 100),
            Point(75, 110), # spike
            Point(99, 100),
            Point(100, 130), # spike but c > 0.5
            Point(100.2, 60),
            Point(100, 90), # zig-zag but c > 0.1
            Point(99.8, 0), # spike
            Point(99.5, 50),
            Point(70, 55),
            Point(60, 50), # not zig-zag
            Point(0, 50)
        ]])
        acute_thr = 5
        straight_thr = 5
        threshold = 0.5
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(50, 50.4).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertFalse(is_spike)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(0, 50.1).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_spike)
        self.assertEqual(ndxa, 1)
        self.assertEqual(round(vx.x(), 4), 50.0016)
        self.assertEqual(vx.y(), 50.0)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(50, 74).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_zigzag)
        self.assertEqual(ndx, 3)
        self.assertEqual(ndxa, 2)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(50, 130).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_spike)
        self.assertEqual(ndx, 4)
        self.assertEqual(ndxa, 5)
        self.assertEqual(vx.x(), 50)
        self.assertEqual(round(vx.y(),4), 99.8374)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(100, 130).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_acute)
        self.assertFalse(is_spike)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(100, 90).get_spike_context(square, acute_thr, straight_thr, 0.1)
        self.assertFalse(is_spike)
        self.assertFalse(is_zigzag)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(100, 0).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_spike)
        self.assertEqual(ndx, 11)
        self.assertEqual(ndxa, 12)
        self.assertEqual(round(vx.x(),4), 99.9109)
        self.assertEqual(round(vx.y(),4), 49.9234)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = \
            Point(60, 50).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertFalse(is_zigzag)


class TestGeometry(unittest.TestCase):

    def test_get_multipolygon(self):
        p = [[Point(0,0), Point(1,0), Point(1,1), Point(0,0)]]
        mp = [[[Point(2,0), Point(3,0), Point(3,1), Point(2,0)]], p]
        f = QgsFeature(QgsFields())
        g = Geometry.fromPolygonXY(p)
        f.setGeometry(g)
        self.assertEqual(Geometry.get_multipolygon(f), [p])
        self.assertEqual(Geometry.get_multipolygon(g), [p])
        g = Geometry.fromMultiPolygonXY(mp)
        f.setGeometry(g)
        self.assertEqual(Geometry.get_multipolygon(f), mp)
        self.assertEqual(Geometry.get_multipolygon(g), mp)

    def test_get_vertices_list(self):
        p = [[Point(0,0), Point(1,0), Point(1,1), Point(0,0)]]
        mp = [[[Point(2,0), Point(3,0), Point(3,1), Point(2,0)]], p]
        f = QgsFeature(QgsFields())
        f.setGeometry(Geometry.fromMultiPolygonXY(mp))
        v = [mp[0][0][0], mp[0][0][1], mp[0][0][2], p[0][0], p[0][1], p[0][2]]
        self.assertEqual(Geometry.get_vertices_list(f), v)

    def test_get_outer_vertices(self):
        p1 = [Point(1,1), Point(2,1), Point(2,2), Point(1,1)]
        p2 = [Point(0,0), Point(3,0), Point(3,3), Point(0,0)]
        p3 = [Point(4,0), Point(5,0), Point(5,1), Point(4,0)]
        mp = [[p1, p2], [p3]]
        f = QgsFeature(QgsFields())
        f.setGeometry(Geometry.fromMultiPolygonXY(mp))
        v = p1[:-1] + p3[:-1]
        self.assertEqual(Geometry.get_outer_vertices(f), v)


class TestBaseLayer(unittest.TestCase):

    def setUp(self):
        self.fixture = QgsVectorLayer('test/building.gml', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid())
        fn = 'test_layer.shp'
        BaseLayer.create_shp(fn, self.fixture.crs())
        self.layer = PolygonLayer(fn, 'building', 'ogr')
        self.assertTrue(self.layer.isValid())
        fields1 = []
        fields1.append(QgsField("A", QVariant.String))
        fields1.append(QgsField("B", QVariant.Int))
        self.layer.writer.addAttributes(fields1)
        self.layer.updateFields()

    def tearDown(self):
        del self.layer
        BaseLayer.delete_shp('test_layer.shp')

    def test_copy_feature_with_resolve(self):
        feature = next(self.fixture.getFeatures())
        resolve = { 'A': ('gml_id', '[0-9]+[A-Z]+[0-9]+[A-Z]') }
        new_fet = self.layer.copy_feature(feature, resolve=resolve)
        self.assertEqual(feature['localId'], new_fet['A'])
        resolve = { 'A': ('gml_id', 'Foo[0-9]+') }
        new_fet = self.layer.copy_feature(feature, resolve=resolve)
        self.assertEqual(new_fet['A'], None)

    def test_copy_feature_with_rename(self):
        feature = next(self.fixture.getFeatures())
        rename = {"A": "gml_id", "B": "value"}
        new_fet = self.layer.copy_feature(feature, rename)
        self.assertEqual(feature['gml_id'], new_fet['A'])
        self.assertEqual(feature['value'], new_fet['B'])
        self.assertTrue(feature.geometry().equals(new_fet.geometry()))

    def test_copy_feature_all_fields(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.startEditing())
        self.assertTrue(layer.isValid())
        feature = next(self.fixture.getFeatures())
        new_fet = layer.copy_feature(feature)
        self.assertTrue(layer.commitChanges())
        self.assertEqual(feature['gml_id'], new_fet['gml_id'])
        self.assertEqual(feature['localId'], new_fet['localId'])
        self.assertTrue(feature.geometry().equals(new_fet.geometry()))

    @mock.patch('layer.tqdm')
    def test_append_with_rename(self, m_tqdm):
        rename = {"A": "gml_id", "B": "value"}
        self.layer.append(self.fixture, rename)
        self.assertEqual(self.layer.featureCount(), self.fixture.featureCount())
        feature = next(self.fixture.getFeatures())
        new_fet = next(self.layer.getFeatures())
        self.assertEqual(feature['gml_id'], new_fet['A'])

    @mock.patch('layer.tqdm')
    def test_append_all_fields(self, m_tqdm):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        layer.append(self.fixture)
        feature = next(self.fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature['gml_id'], new_fet['gml_id'])
        self.assertEqual(feature['localId'], new_fet['localId'])

    @mock.patch('layer.tqdm')
    def test_append_with_query(self, m_tqdm):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        declined_filter = lambda feat, kwargs: feat['conditionOfConstruction'] == 'declined'
        layer.append(self.fixture, query=declined_filter)
        self.assertEqual(layer.featureCount(), 2)

    @mock.patch('layer.tqdm')
    def test_append_void(self, m_tqdm):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        declined_filter = lambda feat, kwargs: feat['conditionOfConstruction'] == 'foobar'
        layer.append(self.fixture, query=declined_filter)
        self.assertEqual(layer.featureCount(), 0)

    @mock.patch('layer.tqdm')
    @mock.patch('layer.Geometry')
    def test_append_void_geometry(self, m_geom, m_tqdm):
        m_geom.get_multipolygon.return_value = []
        m_layer = mock.MagicMock()
        feat = mock.MagicMock()
        m_layer.getFeatures.return_value = [feat]
        tl = mock.MagicMock()
        f = BaseLayer.append
        tl.append = getattr(f, '__func__', f)
        tl.append(tl, m_layer)
        self.assertFalse(tl.writer.addFeatures.called)
        feat.geometry.return_value.wkbType.assert_called_once_with()
        feat.geometry.return_value.wkbType.return_value = WKBPoint
        tl.append(tl, m_layer)
        self.assertTrue(tl.writer.addFeatures.called)

    def test_add_delete(self):
        feat = QgsFeature(self.layer.fields())
        feat['A'] = 'foobar'
        feat['B'] = 123
        self.assertEqual(self.layer.featureCount(), 0)
        self.layer.writer.addFeatures([feat])
        self.assertEqual(self.layer.featureCount(), 1)
        self.layer.writer.deleteFeatures([feat.id()])
        self.assertEqual(self.layer.featureCount(), 0)

    @mock.patch('layer.tqdm')
    def test_translate_field(self, m_tqdm):
        ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        feat = next(self.fixture.getFeatures())
        geom = QgsGeometry(feat.geometry())
        self.assertTrue(geom.isGeosValid())
        translations = {}
        to_add = []
        for i in range(30):
            feat = QgsFeature(self.layer.fields())
            value = ''.join([random.choice(ascii_uppercase) for j in range(10)])
            translations[value] = value.lower()
            feat['A'] = value
            to_add.append(feat)
        feat = QgsFeature(self.layer.fields())
        feat['A'] = 'FooBar'
        to_add.append(feat)
        self.layer.writer.addFeatures(to_add)
        self.assertGreater(self.layer.featureCount(), 0)
        self.layer.translate_field('TAZ', {})
        self.layer.translate_field('A', translations)
        for feat in self.layer.getFeatures():
            self.assertNotEqual(feat['A'], 'FooBar')
            self.assertEqual(feat['A'], feat['A'].lower())
        self.layer.translate_field('A', translations, clean=False)
        self.assertGreater(self.layer.featureCount(), 0)

    @mock.patch('layer.tqdm')
    def test_boundig_box(self, m_tqdm):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.bounding_box(), None)
        bbox = "28.23518053,-16.45257255,28.23557298,-16.45166103"
        layer.append(self.fixture)
        self.assertEqual(layer.bounding_box(), bbox)

    @mock.patch('layer.tqdm')
    def test_reproject(self, m_tqdm):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        layer.append(self.fixture)
        features_before = layer.featureCount()
        feature_in = next(layer.getFeatures())
        geom_in = feature_in.geometry()
        crs_before = layer.crs()
        layer.reproject()
        feature_out = next(layer.getFeatures())
        self.assertEqual(layer.featureCount(), features_before)
        self.assertEqual(layer.crs(), QgsCoordinateReferenceSystem(4326))
        crs_transform = ggs2coordinate_transform(layer.crs(), crs_before)
        geom_out = feature_out.geometry()
        geom_out.transform(crs_transform)
        self.assertLess(abs(geom_in.area() - geom_out.area()), 1E8)
        self.assertEqual(feature_in.attributes(), feature_out.attributes())
        layer.reproject(crs_before)
        feature_out = next(layer.getFeatures())
        geom_out = feature_out.geometry()
        self.assertLess(abs(geom_in.area() - geom_out.area()), 1E8)
        self.assertEqual(feature_in.attributes(), feature_out.attributes())

    @mock.patch('layer.QgsSpatialIndex')
    def test_get_index(self, m_index):
        layer = mock.MagicMock()
        layer.test = BaseLayer.get_index.__func__ if six.PY2 else BaseLayer.get_index
        layer.featureCount.return_value = 0
        layer.test(layer)
        m_index.assert_called_once_with()
        layer.featureCount.return_value = 1
        layer.test(layer)
        m_index.assert_called_with(layer.getFeatures.return_value)

    def test_to_osm(self):
        data = self.layer.to_osm(upload='always', tags={'comment': 'tryit'})
        for (key, value) in setup.changeset_tags.items():
            if key == 'comment':
                self.assertEqual(data.tags[key], 'tryit')
            else:
                self.assertEqual(data.tags[key], value)

class TestBaseLayer2(unittest.TestCase):

    @mock.patch('layer.QgsVectorFileWriter')
    @mock.patch('layer.os')
    def test_export_default(self, mock_os, mock_fw):
        layer = BaseLayer("Polygon", "test", "memory")
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        mock_fw.writeAsVectorFormat.return_value = QgsVectorFileWriter.NoError
        mock_fw.NoError = QgsVectorFileWriter.NoError
        self.assertTrue(layer.export('foobar'))
        mock_fw.deleteShapeFile.assert_called_once_with('foobar')
        mock_fw.writeAsVectorFormat.assert_called_once_with(layer, 'foobar',
            'utf-8', layer.crs(), 'ESRI Shapefile')

    @mock.patch('layer.QgsCoordinateReferenceSystem')
    @mock.patch('layer.QgsVectorFileWriter')
    @mock.patch('layer.os')
    def test_export_other(self, mock_os, mock_fw, mock_crs):
        layer = BaseLayer("Polygon", "test", "memory")
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        layer.export('foobar', 'foo', target_crs_id=1234)
        mock_crs.assert_called_once_with(1234)
        mock_fw.writeAsVectorFormat.assert_called_once_with(layer, 'foobar',
            'utf-8', mock_crs.return_value, 'foo')
        mock_os.remove.assert_called_once_with('foobar')
        layer.export('foobar', 'foo', overwrite=False)
        mock_os.remove.assert_called_once_with('foobar')

class TestPolygonLayer(unittest.TestCase):

    @mock.patch('layer.tqdm')
    def setUp(self, m_tqdm):
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        fn = 'test_layer.shp'
        PolygonLayer.create_shp(fn, self.fixture.crs())
        self.layer = PolygonLayer(fn, 'building', 'ogr')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.append(self.fixture, rename='')
        self.assertEqual(self.layer.featureCount(), self.fixture.featureCount())

    def tearDown(self):
        del self.layer
        PolygonLayer.delete_shp('test_layer.shp')

    def test_get_area(self):
        area = self.layer.get_area()
        self.assertEqual(round(area, 1), 1140234.8)

    @mock.patch('layer.tqdm')
    def test_explode_multi_parts(self, m_tqdm):
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

    def test_get_parents_per_vertex_and_geometries(self):
        (parents_per_vertex, geometries) = self.layer.get_parents_per_vertex_and_geometries()
        self.assertEqual(len(geometries), self.layer.featureCount())
        self.assertTrue(all([Geometry.get_multipolygon(geometries[f.id()]) == \
            Geometry.get_multipolygon(f)
                for f in self.layer.getFeatures()]))
        self.assertGreater(len(parents_per_vertex), 0)
        self.assertTrue(all([Geometry.fromPointXY(vertex).intersects(geometries[fid])
            for (vertex, fids) in list(parents_per_vertex.items()) for fid in fids]))

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

    @mock.patch('layer.tqdm')
    def test_difference(self, m_tqdm):
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


class TestParcelLayer(unittest.TestCase):

    def test_init(self):
        layer = ParcelLayer()
        self.assertEqual(layer.fields()[0].name(), 'localId')
        self.assertEqual(layer.fields()[1].name(), 'label')
        self.assertEqual(layer.rename['localId'], 'inspireId_localId')

    def test_not_empty(self):
        layer = ParcelLayer('test/building.gml', 'building', 'ogr')
        self.assertEqual(len(layer.fields().toList()), 23)


class TestZoningLayer(unittest.TestCase):

    @mock.patch('layer.tqdm')
    def setUp(self, m_tqdm):
        self.fixture = QgsVectorLayer('test/zoning.gml', 'zoning', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        fn = 'urban_zoning.shp'
        ZoningLayer.create_shp(fn, self.fixture.crs())
        self.layer1 = ZoningLayer('u{:05}', fn, 'urbanzoning', 'ogr')
        self.assertTrue(self.layer1.isValid(), "Init QGIS")
        fn = 'rustic_zoning.shp'
        ZoningLayer.create_shp(fn, self.fixture.crs())
        self.layer2 = ZoningLayer('r{:03}', fn, 'rusticzoning', 'ogr')
        self.assertTrue(self.layer2.isValid(), "Init QGIS")
        self.layer1.append(self.fixture, 'M')
        self.layer2.append(self.fixture, 'P')
        
    def test_append(self):
        self.assertGreater(self.layer1.featureCount() + self.layer2.featureCount(),
            self.fixture.featureCount())
        for f in self.layer1.getFeatures():
            self.assertEqual(f['levelName'][3], 'M')
            self.assertFalse(len(Geometry.get_multipolygon(f)) > 1)
        for f in self.layer2.getFeatures():
            self.assertEqual(f['levelName'][3], 'P')
            self.assertFalse(len(Geometry.get_multipolygon(f)) > 1)

    @mock.patch('layer.tqdm')
    @mock.patch('layer.Geometry')
    def test_append_void_geometry(self, m_geom, m_tqdm):
        m_geom.get_multipolygon.return_value = []
        m_layer = mock.MagicMock()
        m_layer.getFeatures.return_value = [mock.MagicMock()]
        m_layer.dataProvider.return_value.fieldNameIndex.return_value = 1
        zoning = mock.MagicMock()
        f = ZoningLayer.append
        zoning.append = getattr(f, '__func__', f)
        zoning.append(zoning, m_layer, level=None)
        self.assertFalse(zoning.writer.addFeatures.called)

    def tearDown(self):
        del self.layer1
        ZoningLayer.delete_shp('urban_zoning.shp')
        del self.layer2
        ZoningLayer.delete_shp('rustic_zoning.shp')

    def test_get_adjacents_and_geometries(self):
        (groups, geometries) = self.layer1.get_adjacents_and_geometries()
        self.assertTrue(all([len(g) > 1 for g in groups]))
        for group in groups:
            for other in groups:
                if group != other:
                    self.assertTrue(all(p not in other for p in group))

    def test_merge_adjacents(self):
        self.layer1.merge_adjacents()
        (groups, geometries) = self.layer1.get_adjacents_and_geometries()
        self.assertEqual(len(groups), 0)
        
    def test_set_tasks(self):
        self.layer1.set_tasks('12345')
        labels = {int(f['label'][1:]) for f in self.layer1.getFeatures()}
        self.assertEqual(max(labels), len(labels))
        self.assertEqual(min(labels), 1)
        self.assertEqual(next(self.layer1.getFeatures())['zipcode'], '12345')
        self.layer2.set_tasks('12345')        
        labels = {int(f['label'][1:]) for f in self.layer2.getFeatures()}
        self.assertEqual(max(labels), len(labels))
        self.assertEqual(min(labels), 1)
        self.assertEqual(next(self.layer2.getFeatures())['zipcode'], '12345')
        
    @mock.patch('layer.tqdm')
    def test_set_cons_tasks(self, m_tqdm):
        test = Counter({'86416': 198, '84428': 89, '88423': 86, '86417': 70,
            '89423': 61, '86423': 57, '87427': 53, '86439': 45, '86464': 38,
            '85426': 34, '89403': 33, '86435': 32, '86434': 28, '88429': 27,
            '90417': 27, '88427': 26, '91441': 26, '90425': 23, '85449': 22,
            '013': 21, '88405': 19, '83424': 17, '86448': 16, '83429': 15,
            '87459': 14, '85411': 14, '87425': 12, '85439': 12, '82426': 9,
            '88416': 9, '90424': 8, '86433': 7, '004': 7, '005': 6,
            '89414': 6, '83428': 5, '86459': 4, '90429': 4, '86427': 4,
            '88428': 3, '88393': 3, '86449': 2, '89415': 2, '003': 1})
        fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        building = ConsLayer()
        building.append(fixture)
        building.set_tasks(self.layer1, self.layer2)
        tasks = Counter()
        for feat in building.getFeatures():
            if feat['task'] is None:
                self.assertEqual(feat['localId'], '000902900CS52D_part1')
            else:
                tasks[feat['task']] += 1
        self.assertEqual(tasks, test)


class TestConsLayer(unittest.TestCase):

    @mock.patch('layer.tqdm')
    def setUp(self, m_tqdm):
        self.fixture = QgsVectorLayer('test/cons.shp', 'building', 'ogr')
        self.assertTrue(self.fixture.isValid(), "Loading fixture")
        fn = 'test_layer.shp'
        ConsLayer.create_shp(fn, self.fixture.crs())
        self.layer = ConsLayer(fn, 'zoning', 'ogr')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.append(self.fixture, rename='')
        self.assertEqual(self.layer.featureCount(), self.fixture.featureCount())

    def tearDown(self):
        del self.layer
        ConsLayer.delete_shp('test_layer.shp')

    def test_is_building(self):
        self.assertTrue(ConsLayer.is_building({'localId': 'foobar'}))
        self.assertFalse(ConsLayer.is_building({'localId': 'foo_bar'}))

    def test_is_part(self):
        self.assertTrue(ConsLayer.is_part({'localId': 'foo_part1'}))
        self.assertFalse(ConsLayer.is_part({'localId': 'foo_PI.1'}))

    def test_is_pool(self):
        self.assertTrue(ConsLayer.is_pool({'localId': 'foo_PI.1'}))
        self.assertFalse(ConsLayer.is_pool({'localId': 'foo_part1'}))

    def test_merge_adjacent_features(self):
        parts = [p for p in self.layer.search("localId like '8840501CS5284S_part%%'")]
        geom = Geometry.merge_adjacent_features(parts)
        area = sum([p.geometry().area() for p in parts])
        self.assertEqual(100*round(geom.area(), 2), 100*round(area, 2))
        self.assertGreater(len(Geometry.get_multipolygon(geom)), 0)
        self.assertLess(len(Geometry.get_multipolygon(geom)), len(parts))

    @mock.patch('layer.tqdm')
    def test_explode_multi_parts(self, m_tqdm):
        mp0 = [f for f in self.layer.getFeatures()
            if len(Geometry.get_multipolygon(f)) > 1]
        self.assertGreater(len(mp0), 0)
        address = AddressLayer()
        address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        address.append(address_gml)
        refs = {ad['localId'].split('.')[-1] for ad in address.getFeatures()}
        mp1 = [f for f in self.layer.getFeatures() if f['localId'] in refs and
            len(Geometry.get_multipolygon(f)) > 1]
        self.assertGreater(len(mp1), 0)
        self.layer.explode_multi_parts(address)
        mp2 = [f for f in self.layer.getFeatures()
            if len(Geometry.get_multipolygon(f)) > 1]
        self.assertEqual(len(mp1), len(mp2))

    @mock.patch('layer.tqdm')
    def test_append_building(self, m_tqdm):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/building.gml', 'building', 'ogr')
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = next(fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature['conditionOfConstruction'], new_fet['condition'])
        self.assertEqual(feature['localId'], new_fet['localId'])

    @mock.patch('layer.tqdm')
    def test_append_buildingpart(self, m_tqdm):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/buildingpart.gml', 'building', 'ogr')
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = next(fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature['numberOfFloorsAboveGround'], new_fet['lev_above'])
        self.assertEqual(feature['localId'], new_fet['localId'])

    @mock.patch('layer.tqdm')
    def test_append_othercons(self, m_tqdm):
        layer = ConsLayer()
        self.assertTrue(layer.isValid(), "Init QGIS")
        fixture = QgsVectorLayer('test/othercons.gml', 'building', 'ogr')
        self.assertTrue(fixture.isValid())
        layer.append(fixture)
        feature = next(fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature['constructionNature'], new_fet['nature'])
        self.assertEqual(feature['localId'], new_fet['localId'])

    @mock.patch('layer.tqdm')
    def test_append_cons(self, m_tqdm):
        exp = QgsExpression("nature = 'openAirPool'")
        request = QgsFeatureRequest(exp)
        feat = next(self.layer.getFeatures(request))
        self.assertNotEqual(feat, None)
        layer = ConsLayer()
        layer.rename = {}
        layer.append(self.layer)
        feat = next(layer.getFeatures(request))
        self.assertNotEqual(feat, None)

    @mock.patch('layer.tqdm')
    def test_remove_parts_below_ground(self, m_tqdm):
        to_clean = [f.id() for f in self.layer.search('lev_above=0 and lev_below>0')]
        self.assertGreater(len(to_clean), 0, 'There are parts below ground')
        self.layer.remove_outside_parts()
        to_clean = [f.id() for f in self.layer.search('lev_above=0 and lev_below>0')]
        self.assertEqual(len(to_clean), 0, 'There are not parts below ground')

    def test_index_of_parts(self):
        parts = self.layer.index_of_parts()
        p = {f.id(): f for f in self.layer.getFeatures() if self.layer.is_part(f)}
        self.assertEqual(sum(len(g) for g in list(parts.values())), len(p))
        for (localid, group) in list(parts.items()):
            for pa in group:
                self.assertTrue(localid, pa['localid'].split('_')[0])
                self.assertIn('_', pa['localid'])

    def test_index_of_building_and_parts(self):
        (buildings, parts) = self.layer.index_of_building_and_parts()
        b = [f for f in self.layer.getFeatures() if self.layer.is_building(f)]
        p = [f for f in self.layer.getFeatures() if self.layer.is_part(f)]
        self.assertEqual(sum(len(g) for g in list(buildings.values())), len(b))
        self.assertEqual(sum(len(g) for g in list(parts.values())), len(p))
        self.assertTrue(all([localid==bu['localid']
            for (localid, group) in list(buildings.items()) for bu in group]))
        self.assertTrue(all([localid==pa['localid'][0:14]
            for (localid, group) in list(parts.items()) for pa in group]))

    @mock.patch('layer.tqdm')
    def test_remove_outside_parts(self, m_tqdm):
        refs = [
            '8742721CS5284S_part10',
            '8742721CS5284S_part5',
            '8742708CS5284S_part1',
            '8742707CS5284S_part2',
            '8742707CS5284S_part6'
        ]
        exp = QgsExpression("localId = '000902900CS52D'")
        request = QgsFeatureRequest(exp)
        with self.assertRaises(StopIteration):
            next(self.layer.getFeatures(request))
        self.layer.remove_outside_parts()
        f = next(self.layer.getFeatures(request))
        self.assertEqual(f['localId'], '000902900CS52D')
        for feat in self.layer.getFeatures():
            self.assertNotIn(feat['localId'], refs)

    @mock.patch('layer.tqdm')
    def test_get_parts(self, m_tqdm):
        self.layer.explode_multi_parts()
        parts = [p for p in self.layer.search("localId like '8840501CS5284S_part%%'")]
        for footprint in self.layer.search("localId = '8840501CS5284S'"):
            parts_inside = [p for p in parts if is_inside(p, footprint)]
            parts_for_level, max_level, min_level = self.layer.get_parts(footprint, parts)
            max_levelc = max([p['lev_above'] for p in parts_inside])
            min_levelc = max([p['lev_below'] for p in parts_inside])
            self.assertEqual(len(parts_inside), sum([len(p) for p in list(parts_for_level.values())]))
            for part in parts_inside:
                self.assertIn(part, parts_for_level[(part['lev_above'], part['lev_below'])]) 
            self.assertEqual(max_level, max_levelc)
            self.assertEqual(min_level, min_levelc)

    @mock.patch('layer.tqdm')
    def test_merge_adjacent_parts(self, m_tqdm, ref=None):
        if ref == None:
            self.layer.explode_multi_parts()
            ref = '8842323CS5284S'
        parts = [p for p in self.layer.search("localId like '%s_part%%'" % ref)]
        for footprint in self.layer.search("localId = '%s'" % ref):
            cn, cng, ch, chg= self.layer.merge_adjacent_parts(footprint, parts)
            parts_for_level, max_level, min_level = self.layer.get_parts(footprint, parts)
            if len(parts_for_level) > 1:
                areap = 0
                for level, group in list(parts_for_level.items()):
                    geom = Geometry.merge_adjacent_features(group)
                    poly = Geometry.get_multipolygon(geom)
                    if len(poly) < len(group):
                        areap += geom.area()
                aream = sum([g.area() for g in list(chg.values())])
                self.assertEqual(100*round(areap, 2), 100*round(aream, 2))
                self.assertEqual(len(cn), 0)
            else:
                self.assertEqual(set(cn), set([p.id() for p in parts_for_level[max_level, min_level]]))
            self.assertEqual(max([l[0] for l in list(parts_for_level.keys())]), max_level)
            self.assertEqual(max([l[1] for l in list(parts_for_level.keys())]), min_level)
            self.assertEqual(ch[footprint.id()][6], max_level)
            self.assertEqual(ch[footprint.id()][7], min_level)

    @mock.patch('layer.tqdm')
    def test_merge_building_parts(self, m_tqdm):
        self.layer.remove_outside_parts()
        self.layer.merge_building_parts()
        for ref in self.layer.getFeatures():
            if self.layer.is_building(ref):
                self.test_merge_adjacent_parts(ref)

    @mock.patch('layer.tqdm')
    def test_add_topological_points(self, m_tqdm):
        refs = [
            ('8842708CS5284S', Point(358821.08, 3124205.68), 0),
            ('8842708CS5284S_part1', Point(358821.08, 3124205.68), 0),
            ('8942328CS5284S', Point(358857.04, 3124248.6705), 1),
            ('8942328CS5284S_part3', Point(358857.04, 3124248.6705), 0)
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

    @mock.patch('layer.tqdm')
    def test_delete_invalid_geometries(self, m_tqdm):
        f1 = QgsFeature(self.layer.fields())
        g1 = Geometry.fromPolygonXY([[
            Point(358794.000, 3124330.000),
            Point(358794.200, 3124329.800),
            Point(358794.400, 3124330.000),
            Point(358794.200, 3124500.000),
            Point(358794.000, 3124330.000)
        ]])
        f1.setGeometry(g1)
        f2 = QgsFeature(self.layer.fields())
        g2 = Geometry.fromPolygonXY([[
            Point(358794.000, 3124330.000),
            Point(358795.000, 3124331.000),
            Point(358794.500, 3124500.000),
            Point(358794.000, 3124330.000)
        ]])
        f2.setGeometry(g2)
        f3 = QgsFeature(self.layer.fields())
        g3 = Geometry.fromPolygonXY([[
            Point(358890.000, 3124329.000),
            Point(358900.000, 3124329.000),
            Point(358900.000, 3124501.000),
            Point(358890.000, 3124501.000),
            Point(358890.000, 3124330.000)
        ], [
            Point(358894.000, 3124330.000),
            Point(358895.000, 3124331.000),
            Point(358894.500, 3124500.000),
            Point(358894.000, 3124330.000)
        ]])
        f3.setGeometry(g3)
        f4 = QgsFeature(self.layer.fields())
        g4 = Geometry.fromPolygonXY([[
            Point(357400.00, 3124305.00), # spike
            Point(357405.00, 3124305.04),
            Point(357404.99, 3124307.60),
            Point(357405.00, 3124307.40), # zig-zag
            Point(357405.00, 3124313.00), # spike
            Point(357405.04, 3124310.00),
            Point(357407.50, 3124311.00),
            Point(357409.96, 3124310.00),
            Point(357410.00, 3124313.00), # spike
            Point(357410.02, 3124306.00),
            Point(357410.00, 3124305.00),
            Point(357400.00, 3124305.00),
        ]])
        f4.setGeometry(g4)
        f5 = QgsFeature(self.layer.fields())
        g5 = Geometry.fromPolygonXY([[
            Point(357400.00, 3124305.00),
            Point(357405.00, 3124305.04),
            Point(357405.00, 3124310.00),
            Point(357400.00, 3124310.00),
            Point(357400.00, 3124305.00)
        ]])
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
        r = [(357410.00, 3124305.00), 
            (357405.00, 3124305.00), 
            (357405.00, 3124309.98), 
            (357407.50, 3124311.00), 
            (357410.01, 3124310.02), 
            (357410.02, 3124306.00), 
            (357410.00, 3124305.00)]
        self.assertEqual(r, [(round(p.x(), 2), round(p.y(), 2)) for p in mp[0][0]])
        request = QgsFeatureRequest().setFilterFid(self.layer.featureCount() - 1)
        f = next(self.layer.getFeatures(request))
        mp = Geometry.get_multipolygon(f)
        r = [(357400.00, 3124305.00), 
            (357400.00, 3124310.00), 
            (357405.00, 3124310.00), 
            (357405.00, 3124305.00), 
            (357400.00, 3124305.00)]
        self.assertEqual(r, [(round(p.x(), 2), round(p.y(), 2)) for p in mp[0][0]])

    @mock.patch('layer.tqdm')
    def test_simplify1(self, m_tqdm):
        refs = [
            ('8643326CS5284S', Point(358684.62, 3124377.54), True),
            ('8643326CS5284S', Point(358686.29, 3124376.11), True),
            ('8643324CS5284S', Point(358677.29, 3124366.64), False),
        ]
        self.layer.explode_multi_parts()
        self.layer.simplify()
        for ref in refs:
            building = next(self.layer.search("localId = '%s'" % ref[0]))
            self.assertEqual(ref[1] in Geometry.get_multipolygon(building)[0][0], ref[2])

    @mock.patch('layer.tqdm')
    def test_simplify2(self, m_tqdm):
        layer = ConsLayer()
        writer = layer.dataProvider()
        fixture1 = QgsVectorLayer('test/38023.buildingpart.gml', 'building', 'ogr')
        self.assertTrue(fixture1.isValid(), "Loading fixture")
        layer.append(fixture1, rename='')
        self.assertEqual(layer.featureCount(), fixture1.featureCount())
        fixture2 = QgsVectorLayer('test/38023.buildingpart.gml', 'buildingpart', 'ogr')
        self.assertTrue(fixture2.isValid(), "Loading fixture")
        layer.append(fixture2, rename='')
        self.assertEqual(layer.featureCount(), fixture1.featureCount() + fixture2.featureCount())
        layer.remove_outside_parts()
        layer.explode_multi_parts()
        layer.topology()
        layer.simplify()
        for feat in layer.getFeatures():
            geom = feat.geometry()
            self.assertTrue(geom.isGeosValid(), feat['localId'])
        layer.merge_building_parts()

    @mock.patch('layer.tqdm')
    def test_move_address(self, m_tqdm):
        refs = {
            '38.012.10.10.8643403CS5284S': 'Entrance',
            '38.012.10.11.8842304CS5284S': 'Entrance',
            #'38.012.10.13.8842305CS5284S': 'Entrance',
            '38.012.10.14.8643404CS5284S': 'corner',
            '38.012.10.14.8643406CS5284S': 'Parcel',
            '38.012.10.2.8642321CS5284S': 'Entrance',
            '38.012.15.73.8544911CS5284S': 'remote'
        }
        self.layer.explode_multi_parts()
        address = AddressLayer()
        address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        address.append(address_gml)
        self.assertEqual(address.featureCount(), 14)
        self.layer.move_address(address)
        self.assertEqual(address.featureCount(), 6)
        for ad in address.getFeatures():
            if ad['localId'] in list(refs.keys()):
                self.assertEqual(ad['spec'], refs[ad['localId']])
                if ad['spec'] == 'Entrance':
                    refcat = ad['localId'].split('.')[-1]
                    building = next(self.layer.search("localId = '%s'" % refcat))
                    self.assertTrue(ad.geometry().touches(building.geometry()))
        self.layer.move_address(address)
        self.assertEqual(address.featureCount(), 6)

    @mock.patch('layer.tqdm')
    def test_validate(self, m_tqdm):
        self.layer.merge_building_parts()
        max_level = {}
        min_level = {}
        self.layer.validate(max_level, min_level)
        refs = ['7239208CS5273N', '38012A00400007']
        for (l, v) in list({1: 126, 2: 114, 3: 67, 4: 16, 5: 1}.items()):
            self.assertEqual(Counter(list(max_level.values()))[l], v)
        for (l, v) in list({1: 68, 2: 2}.items()):
            self.assertEqual(Counter(list(min_level.values()))[l], v)
        for ref in refs:
            exp = QgsExpression("localId = '%s'" % ref)
            request = QgsFeatureRequest(exp)
            feat = next(self.layer.getFeatures(request))
            self.assertNotEqual(feat['fixme'], '')
    
    def test_to_osm(self):
        data = self.layer.to_osm(upload='always')
        self.assertEqual(data.upload, 'always')
        ways = 0
        rels = 0
        c = Counter()
        for feat in self.layer.getFeatures():
            p = Geometry.get_multipolygon(feat)
            ways += sum([len(s) for s in p])
            rels += (1 if len(p) + len(p[0]) > 2 else 0)
        self.assertEqual(ways, len(data.ways))
        self.assertEqual(rels, len(data.relations))

    @mock.patch('layer.tqdm')
    def test_conflate(self, m_tqdm):
        self.layer.reproject()
        d = osm.Osm()
        d.Way(((-16.44211325828, 28.23715394977), (-16.44208978895, 28.23714124855),
            (-16.44209884141, 28.23712884271), (-16.44212197546, 28.23714361157),
            (-16.44211325828, 28.23715394977)), dict(building='yes', ref='1'))
        d.Way(((-16.44016295806, 28.23657619128), (-16.43985450402, 28.23641077902),
            (-16.43991753593, 28.23632689127), (-16.44020855561, 28.23648403305),
            (-16.44016295806, 28.23657619128)), dict(building='yes', ref='2'))
        d.Way(((-16.44051231511, 28.23655551417), (-16.44042112, 28.23650529975),
            (-16.4405699826, 28.23631153095), (-16.44065782495, 28.23635288407),
            (-16.44051231511, 28.23655551417)), dict(building='yes', ref='3'))
        self.assertEqual(len(d.ways), 3)
        self.layer.conflate(d, delete=False)
        self.assertEqual(len(d.ways), 3)
        for el in d.ways:
            self.assertEqual('conflict' in el.tags, el.tags['ref'] == '3')
        d.Way(((-16.44038491018, 28.23645095), (-16.44029706784, 28.23640132629),
            (-16.44042514332, 28.23624713819), (-16.44049689241, 28.23629558045),
            (-16.44038491018, 28.23645095)), dict(building='yes', ref='4'))
        d.Way(((-16.44019514591, 28.23634461522), (-16.44002616674, 28.23625009376),
            (-16.44011199743, 28.23611540052), (-16.44027829438, 28.23619810692)),
            dict(building='yes', ref='5'))
        d.Way(((-16.43993497163, 28.23591926797), (-16.43972575933, 28.23580584175),
            (-16.4398062256, 28.23610122228), (-16.43959701329, 28.23598543321),
            (-16.43993497163, 28.23591926797)), dict(building='yes', ref='6'))
        d.Way(((-16.4386775, 28.2360472), (-16.4386158, 28.2363235),
            (-16.4384536, 28.2362954), (-16.4385153, 28.2360191),
            (-16.4386775, 28.2360472)), dict(building='yes', ref='7'))
        d.Way(((-16.4386049, 28.2357006), (-16.4385316, 28.2356401),
            (-16.4385093, 28.2356419), (-16.4384993, 28.2357054),
            (-16.4386049, 28.2357006)), dict(building='yes', ref='8'))
        w0 = d.Way(((-16.4409784, 28.2365733), (-16.4409231, 28.236542),
            (-16.4409179, 28.2365154), (-16.4409268, 28.236504),
            (-16.4408588, 28.236465)))
        w1 = d.Way(((-16.4406755, 28.236688), (-16.4408332, 28.2367735)))
        w2 = d.Way(((-16.4408332, 28.2367735), (-16.4408943, 28.2366893),
            (-16.4409395, 28.2367147), (-16.4409818, 28.2366563),
            (-16.4409366, 28.2366308), (-16.4409784, 28.2365733)))
        w3 = d.Way(((-16.4408588, 28.236465), (-16.4408086, 28.2365319),
            (-16.4407037, 28.2364709), (-16.4406669, 28.2365102),
            (-16.4406513, 28.2365338), (-16.440639, 28.2365663),
            (-16.4407394, 28.2366223), (-16.4407188, 28.2366474),
            (-16.440707, 28.2366405), (-16.4406755, 28.236688)))
        w4 = d.Way(((-16.440072, 28.236560), (-16.439966, 28.236505),
            (-16.439888, 28.236605), (-16.4399860, 28.236666),
            (-16.440072, 28.236560)))
        w5 = d.Way(((-16.439965, 28.236703), (-16.439861, 28.236642),
            (-16.439805, 28.236733), (-16.439903, 28.236790),
            (-16.439965, 28.236703)))
        r1 = d.Relation(tags = dict(building='yes', ref='9'))
        r1.append(w0, 'outer')
        r1.append(w1, 'outer')
        r1.append(w2, 'outer')
        r1.append(w3, 'outer')
        r2 = d.Relation  (tags = dict(building='yes', ref='10'))
        r2.append(w4, 'outer')
        r2.append(w5, 'outer')
        self.assertEqual(len(d.ways), 14)
        self.assertEqual(len(d.relations), 2)
        self.layer.conflate(d)
        self.assertEqual(len(d.ways), 12)
        self.assertEqual(len(d.relations), 2)
        self.assertEqual({e.tags['ref'] for e in d.ways if 'ref' in e.tags},
            {'3', '4', '5', '6', '7', '8'})


class TestAddressLayer(unittest.TestCase):

    def setUp(self):
        self.address_gml = QgsVectorLayer('test/address.gml', 'address', 'ogr')
        self.assertTrue(self.address_gml.isValid(), "Loading address")
        self.tn_gml = QgsVectorLayer('test/address.gml|layername=thoroughfarename', 'tn', 'ogr')
        self.assertTrue(self.tn_gml.isValid(), "Loading thoroughfarename")
        self.pd_gml = QgsVectorLayer('test/address.gml|layername=postaldescriptor', 'pd', 'ogr')
        self.assertTrue(self.pd_gml.isValid(), "Loading address")
        self.au_gml = QgsVectorLayer('test/address.gml|layername=adminUnitname', 'au', 'ogr')
        self.assertTrue(self.au_gml.isValid(), "Loading address")
        fn = 'test_layer.shp'
        AddressLayer.create_shp(fn, self.address_gml.crs())
        self.layer = AddressLayer(fn, 'address', 'ogr')
        self.assertTrue(self.layer.isValid(), "Init QGIS")
        self.layer.dataProvider().addAttributes([QgsField('TN_text', QVariant.String, len=254)])
        self.layer.updateFields()

    def tearDown(self):
        del self.layer
        AddressLayer.delete_shp('test_layer.shp')

    @mock.patch('layer.tqdm')
    def test_append(self, m_tqdm):
        self.layer.append(self.address_gml)
        feat = next(self.layer.getFeatures())
        attrs = ['localId', 'PD_id', 'TN_id', 'AU_id']
        values = ['38.012.1.12.0295603CS6109N', 'ES.SDGC.PD.38.012.38570',
                  'ES.SDGC.TN.38.012.1', 'ES.SDGC.AU.38.012']
        for (attr, value) in zip(attrs, values):
            self.assertEqual(feat[attr], value)

    @mock.patch('layer.tqdm')
    def test_join_field(self, m_tqdm):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.layer.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.layer.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        feat = next(self.layer.getFeatures())
        attrs = ['TN_text', 'AU_text', 'postCode']
        values = ['MC ABASTOS (RESTO)', 'FASNIA', 38570]
        for (attr, value) in zip(attrs, values):
            self.assertEqual(feat[attr], value)

    @mock.patch('layer.tqdm')
    def test_join_field_size(self, m_tqdm):
        layer = PolygonLayer('Point', 'test', 'memory')
        layer.dataProvider().addAttributes([QgsField('A', QVariant.String, len=255)])
        layer.updateFields()
        self.layer.append(self.address_gml)
        self.layer.join_field(layer, 'TN_id', 'gml_id', ['A'], 'TN_')
        self.assertEqual(self.layer.fields().field('TN_A').length(), 254)

    @mock.patch('layer.tqdm')
    def test_join_void(self, m_tqdm):
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.assertEqual(self.layer.featureCount(), 0)

    @mock.patch('layer.tqdm')
    def test_to_osm(self, m_tqdm):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.layer.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.layer.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        self.layer.source_date = 'foobar'
        data = osm.Osm(upload='ifyoudare')
        data.Node(0,0)
        data = self.layer.to_osm(data=data)
        self.assertEqual(data.upload, 'ifyoudare')
        self.assertEqual(data.tags['source:date'], 'foobar')
        self.assertEqual(len(data.elements), self.layer.featureCount() + 1)
        address = {n.tags['ref']: n.tags['addr:street']+n.tags['addr:housenumber'] \
            for n in data.nodes if 'ref' in n.tags}
        for feat in self.layer.getFeatures():
            t = address[feat['localId'].split('.')[-1]]
            self.assertEqual(feat['TN_text']+feat['designator'], t)

    @mock.patch('layer.tqdm')
    def test_conflate(self, m_tqdm):
        self.layer.append(self.address_gml)
        self.layer.join_field(self.tn_gml, 'TN_id', 'gml_id', ['text'], 'TN_')
        self.layer.join_field(self.au_gml, 'AU_id', 'gml_id', ['text'], 'AU_')
        self.layer.join_field(self.pd_gml, 'PD_id', 'gml_id', ['postCode'])
        current_address = ["CJ CALLEJON (FASNIA)12", "CJ CALLEJON (FASNIA)13"]
        self.assertEqual(self.layer.featureCount(), 14)
        self.layer.conflate(current_address)
        self.assertEqual(self.layer.featureCount(), 10)
        self.layer.conflate(current_address)
        self.assertEqual(self.layer.featureCount(), 10)

    def test_get_highway_names(self):
        layer = AddressLayer('test/address.geojson', 'address', 'ogr')
        highway = HighwayLayer('test/highway.geojson', 'highway', 'ogr')
        highway_names = layer.get_highway_names(highway)
        test = {
            'AV PAZ (FASNIA)': 'Avenida la Paz',
            'CL SAN JOAQUIN (FASNIA)': "Calle San Joaquín",
            'CL HOYO (FASNIA)': 'Calle el Hoyo',
            'CJ CALLEJON (FASNIA)': "Calleja/Callejón Callejon (Fasnia)"
        }
        for (k, v) in list(highway_names.items()):
            self.assertEqual(v, test[k])


class TestHighwayLayer(unittest.TestCase):

    def test_init(self):
        layer = HighwayLayer()
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.fields()[0].name(), 'name')
        self.assertEqual(layer.crs().authid(), 'EPSG:4326')

    def test_read_from_osm(self):
        layer = HighwayLayer()
        data = osm.Osm()
        w1 = data.Way(((10,10), (15,15)), {'name': 'FooBar'})
        w2 = data.Way(((20,20), (30,30)))
        r = data.Relation([w2], {'name': 'BarTaz'})
        layer.read_from_osm(data)
        self.assertEqual(layer.featureCount(), 2)
        names = [feat['name'] for feat in layer.getFeatures()]
        self.assertIn('BarTaz', names)
        self.assertIn('FooBar', names)
        for f in layer.getFeatures():
            if f['name'] == 'FooBar':
                self.assertEqual(f.geometry().asPolyline(), [Point(10, 10), Point(15, 15)])
            if f['name'] == 'BarTaz':
                self.assertEqual(f.geometry().asPolyline(), [Point(20, 20), Point(30, 30)])

class TestDebugWriter(unittest.TestCase):

    def test_init(self):
        layer = HighwayLayer()
        writer = DebugWriter('test', layer, 'memory')
        self.assertEqual(writer.fields[0].name(), 'note')
        self.assertEqual(writer.hasError(), 0)

    def test_add_point(self):
        layer = HighwayLayer()
        writer = DebugWriter('test', layer, 'memory')
        writer.add_point(Point(0, 0), 'foobar')
        writer.add_point(Point(0, 0))

