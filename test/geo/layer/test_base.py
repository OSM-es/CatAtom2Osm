import logging
import mock
import random
import unittest

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsFeature, QgsField, QgsGeometry,
    QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

from catatom2osm import config
from catatom2osm.app import QgsSingleton
from catatom2osm.geo import BaseLayer
from catatom2osm.geo.types import WKBPoint

qgs = QgsSingleton()
m_log = mock.MagicMock()
m_log.app_level = logging.INFO


class TestBaseLayer(unittest.TestCase):

    def setUp(self):
        fn = 'test/fixtures/building.gml'
        self.fixture = QgsVectorLayer(fn, 'building', 'ogr')
        self.assertTrue(self.fixture.isValid())
        fn = 'test_layer.shp'
        BaseLayer.create_shp(fn, self.fixture.crs())
        self.layer = BaseLayer(fn, 'building', 'ogr')
        self.assertTrue(self.layer.isValid())
        fields = [QgsField("A", QVariant.String), QgsField("B", QVariant.Int)]
        self.layer.writer.addAttributes(fields)
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

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_append_with_rename(self):
        rename = {"A": "gml_id", "B": "value"}
        self.layer.append(self.fixture, rename)
        self.assertEqual(self.layer.featureCount(), self.fixture.featureCount())
        feature = next(self.fixture.getFeatures())
        new_fet = next(self.layer.getFeatures())
        self.assertEqual(feature['gml_id'], new_fet['A'])

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_append_all_fields(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        layer.append(self.fixture)
        feature = next(self.fixture.getFeatures())
        new_fet = next(layer.getFeatures())
        self.assertEqual(feature['gml_id'], new_fet['gml_id'])
        self.assertEqual(feature['localId'], new_fet['localId'])

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_append_with_query(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        declined_filter = lambda feat, kwargs: feat['conditionOfConstruction'] == 'declined'
        layer.append(self.fixture, query=declined_filter)
        self.assertEqual(layer.featureCount(), 2)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_append_void(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        declined_filter = lambda feat, kwargs: feat['conditionOfConstruction'] == 'foobar'
        layer.append(self.fixture, query=declined_filter)
        self.assertEqual(layer.featureCount(), 0)

    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    @mock.patch('catatom2osm.geo.layer.base.Geometry')
    def test_append_void_geometry(self, m_geom):
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
        # Works in QGIS 2.18.17 but not in 3.16.3
        #self.assertEqual(self.layer.featureCount(), 0)

    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_translate_field(self):
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

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_boundig_box(self):
        layer = BaseLayer("Polygon", "test", "memory")
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.bounding_box(), None)
        bbox = "28.23318053,-16.45457255,28.23757298,-16.44966103"
        layer.append(self.fixture)
        self.assertEqual(layer.bounding_box(), bbox)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
    @mock.patch('catatom2osm.geo.layer.base.tqdm', mock.MagicMock())
    def test_reproject(self):
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
        self.assertEqual(layer.crs(), QgsCoordinateReferenceSystem.fromEpsgId(4326))
        crs_transform = layer.get_crs_transform(layer.crs(), crs_before)
        geom_out = feature_out.geometry()
        geom_out.transform(crs_transform)
        self.assertLess(abs(geom_in.area() - geom_out.area()), 1E8)
        self.assertEqual(feature_in.attributes(), feature_out.attributes())
        layer.reproject(crs_before)
        feature_out = next(layer.getFeatures())
        geom_out = feature_out.geometry()
        self.assertLess(abs(geom_in.area() - geom_out.area()), 1E8)
        self.assertEqual(feature_in.attributes(), feature_out.attributes())

    @mock.patch('catatom2osm.geo.layer.base.QgsSpatialIndex')
    def test_get_index(self, m_index):
        layer = mock.MagicMock()
        layer.test = BaseLayer.get_index
        layer.featureCount.return_value = 0
        layer.test(layer)
        m_index.assert_called_once_with()
        layer.featureCount.return_value = 1
        layer.test(layer)
        m_index.assert_called_with(layer.getFeatures.return_value)

    def test_to_osm(self):
        data = self.layer.to_osm(upload='always', tags={'comment': 'tryit'})
        for (key, value) in config.changeset_tags.items():
            if key == 'comment':
                self.assertEqual(data.tags[key], 'tryit')
            else:
                self.assertEqual(data.tags[key], value)

    def test_search(self):
        fn = 'test/fixtures/building.gml'
        layer = BaseLayer(fn, 'building', 'ogr')
        count = sum([1 for f in layer.search()])
        self.assertEqual(count, layer.featureCount())
        count = sum([1 for f in layer.search("localId LIKE '76407%%'")])
        self.assertEqual(count, 2)


class TestBaseLayer2(unittest.TestCase):

    @mock.patch('catatom2osm.geo.layer.base.BaseLayer.writeAsVectorFormat')
    @mock.patch('catatom2osm.geo.layer.base.QgsVectorFileWriter')
    @mock.patch('catatom2osm.geo.layer.base.os')
    def test_export_default(self, mock_os, mock_fw, mock_wvf):
        layer = BaseLayer("Polygon", "test", "memory")
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        mock_wvf.return_value = QgsVectorFileWriter.NoError
        mock_fw.NoError = QgsVectorFileWriter.NoError
        self.assertTrue(layer.export('foobar'))
        mock_fw.deleteShapeFile.assert_called_once_with('foobar')
        mock_wvf.assert_called_once_with('foobar', 'ESRI Shapefile', layer.crs())

    @mock.patch('catatom2osm.geo.layer.base.QgsVectorFileWriter', mock.MagicMock())
    @mock.patch('catatom2osm.geo.layer.base.BaseLayer.writeAsVectorFormat')
    @mock.patch('catatom2osm.geo.layer.base.QgsCoordinateReferenceSystem.fromEpsgId')
    @mock.patch('catatom2osm.geo.layer.base.os')
    def test_export_other(self, mock_os, mock_crs, mock_wvf):
        layer = BaseLayer("Polygon", "test", "memory")
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        layer.export('foobar', 'foo', target_crs_id=1234)
        crs = mock_crs.return_value
        mock_crs.assert_called_once_with(1234)
        mock_wvf.assert_called_once_with('foobar', 'foo', crs)
        mock_os.remove.assert_called_once_with('foobar')
        layer.export('foobar', 'foo', overwrite=False)
        mock_os.remove.assert_called_once_with('foobar')


class TestBaseLayer2(unittest.TestCase):

    @mock.patch('catatom2osm.geo.layer.base.BaseLayer.writeAsVectorFormat')
    @mock.patch('catatom2osm.geo.layer.base.QgsVectorFileWriter')
    @mock.patch('catatom2osm.geo.layer.base.os')
    def test_export_default(self, mock_os, mock_fw, mock_wvf):
        layer = BaseLayer("Polygon", "test", "memory")
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        mock_wvf.return_value = QgsVectorFileWriter.NoError
        mock_fw.NoError = QgsVectorFileWriter.NoError
        self.assertTrue(layer.export('foobar'))
        mock_fw.deleteShapeFile.assert_called_once_with('foobar')
        mock_wvf.assert_called_once_with('foobar', 'ESRI Shapefile', layer.crs())

    @mock.patch('catatom2osm.geo.layer.base.QgsVectorFileWriter', mock.MagicMock())
    @mock.patch('catatom2osm.geo.layer.base.BaseLayer.writeAsVectorFormat')
    @mock.patch('catatom2osm.geo.layer.base.QgsCoordinateReferenceSystem.fromEpsgId')
    @mock.patch('catatom2osm.geo.layer.base.os')
    def test_export_other(self, mock_os, mock_crs, mock_wvf):
        layer = BaseLayer("Polygon", "test", "memory")
        mock_os.path.exists.side_effect = lambda arg: arg=='foobar'
        layer.export('foobar', 'foo', target_crs_id=1234)
        crs = mock_crs.return_value
        mock_crs.assert_called_once_with(1234)
        mock_wvf.assert_called_once_with('foobar', 'foo', crs)
        mock_os.remove.assert_called_once_with('foobar')
        layer.export('foobar', 'foo', overwrite=False)
        mock_os.remove.assert_called_once_with('foobar')
