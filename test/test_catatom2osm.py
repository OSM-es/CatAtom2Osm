# -*- coding: utf-8 -*-
from builtins import range
from past.builtins import reload
import mock
import unittest
import os, sys
from collections import Counter
from optparse import Values
from qgis.core import QgsVectorLayer
os.environ['LANGUAGE'] = 'C'

import setup
import osm
import layer
import catatom2osm as cat
qgs = cat.QgsSingleton()
import report


def get_func(f):
    return getattr(f, '__func__', f)

class TestQgsSingleton(unittest.TestCase):

    @mock.patch('catatom2osm.QgsSingleton._qgs', None)
    @mock.patch('catatom2osm.gdal')
    @mock.patch('catatom2osm.QgsApplication')
    def test_new(self, m_qgsapp, m_gdal):
        q1 = cat.QgsSingleton()
        self.assertEqual(m_qgsapp.call_count, 1)
        m_gdal.SetConfigOption.assert_has_calls([
            mock.call('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES'),
            mock.call('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        ])
        q2 = cat.QgsSingleton()
        self.assertEqual(m_qgsapp.call_count, 1)
        self.assertTrue(q1 is q2)

class TestCatAtom2Osm(unittest.TestCase):

    def setUp(self):
        self.options = {
            'building': False, 'all': False, 'tasks': True, 'list_zones': False,
            'log_level': 'INFO', 'parcel': False, 'list': False, 'zoning': True,
            'version': False, 'address': False, 'manual': False, 'zone': False,
        }
        self.m_app = mock.MagicMock()
        self.m_app.options = Values(self.options)
        self.m_app.get_translations.return_value = ([], False)
        self.m_app.path = 'foo'
        self.m_app.highway_names_path = 'foo/highway_names.csv'
        self.m_app.label = None
        self.m_app.tasks_path = 'foo/tasks'
        self.m_app.is_new = False

    @mock.patch('catatom2osm.QgsSingleton')
    @mock.patch('catatom.Reader')
    @mock.patch('catatom2osm.report')
    @mock.patch('catatom2osm.os')
    def test_init(self, m_os, m_report, m_cat, m_qgs):
        m_qgs.return_value = 'foo'
        m_cat.return_value.path = 'foo'
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.return_value = False
        self.m_app.init = get_func(cat.CatAtom2Osm.__init__)
        self.m_app.init(self.m_app, 'xxx/12345', self.m_app.options)
        m_cat.assert_called_once_with('xxx/12345')
        self.assertEqual(self.m_app.path, m_cat().path)
        self.assertEqual(m_report.mun_code, m_cat().zip_code)
        self.assertEqual(self.m_app.qgs, 'foo')
        m_os.makedirs.assert_called_once_with('foo/tasks')

    @mock.patch('catatom2osm.gdal')
    def test_gdal(self, m_gdal):
        reload(cat)
        self.assertFalse(m_gdal.PushErrorHandler.called)
        setup.silence_gdal = True
        reload(cat)
        m_gdal.PushErrorHandler.called_once_with('CPLQuietErrorHandler')

    @mock.patch('catatom2osm.report')
    def test_run1(self, m_report):
        self.m_app.run = get_func(cat.CatAtom2Osm.run)
        self.m_app.is_new = False
        building = self.m_app.building
        self.m_app.run(self.m_app)
        self.m_app.process_zoning.assert_called_once_with()
        self.m_app.process_building.assert_called_with()
        self.m_app.read_address.assert_not_called()
        self.m_app.address.to_osm.assert_not_called()
        self.m_app.process_tasks.assert_called_once_with(building)
        self.m_app.process_parcel.assert_not_called()

    @mock.patch('catatom2osm.report')
    def test_run2(self, m_report):
        self.m_app.run = get_func(cat.CatAtom2Osm.run)
        building = self.m_app.building
        address = self.m_app.address
        self.m_app.options = Values({'building': True, 'tasks': False,
            'parcel': True, 'zoning': False, 'address': True, 'manual': False,
            'list_zones': False})
        self.m_app.is_new = False
        building.conflate.return_value = False
        address_osm = self.m_app.address.to_osm.return_value
        building_osm = building.to_osm.return_value
        self.m_app.run(self.m_app)
        self.m_app.process_tasks.assert_not_called()
        self.m_app.process_building.assert_called_once_with()
        self.m_app.read_address.assert_called_once_with()
        current_address = self.m_app.get_current_ad_osm.return_value
        address.conflate.assert_called_once_with(current_address)
        address.to_osm.assert_called_once_with()
        self.m_app.write_osm.assert_called_once_with(address_osm, 'address.osm')
        self.m_app.process_parcel.assert_called_once_with()

    @mock.patch('catatom2osm.report')
    def test_run3(self, m_report):
        self.m_app.run = get_func(cat.CatAtom2Osm.run)
        self.m_app.is_new = False
        self.m_app.options.building = False
        self.m_app.options.tasks = False
        self.m_app.run(self.m_app)
        self.m_app.write_osm.assert_not_called()

    @mock.patch('catatom2osm.report')
    def test_run4(self, m_report):
        del self.m_app.building_gml
        self.m_app.is_new = True
        self.m_app.options.tasks = False
        self.m_app.run = get_func(cat.CatAtom2Osm.run)
        self.m_app.run(self.m_app)
        self.m_app.process_tasks.assert_not_called()

    @mock.patch('catatom2osm.report')
    def test_run5(self, m_report):
        address = self.m_app.address
        self.m_app.run = get_func(cat.CatAtom2Osm.run)
        self.m_app.options = Values({'building': True, 'tasks': False,
            'parcel': False, 'zoning': False, 'address': True, 'manual': True,
            'list_zones': False})
        self.m_app.is_new = False
        building = self.m_app.building
        self.m_app.run(self.m_app)
        address.conflate.assert_not_called()
        building.conflate.assert_not_called()

    @mock.patch('catatom2osm.layer')
    def test_get_building1(self, m_layer):
        self.m_app.get_building = get_func(cat.CatAtom2Osm.get_building)
        x = mock.MagicMock()
        x.source_date = 1
        y = mock.MagicMock()
        z = mock.MagicMock()
        self.m_app.cat.read.side_effect = [x, y, z]
        building = m_layer.ConsLayer.return_value
        self.m_app.get_building(self.m_app)
        fn = os.path.join('foo', 'building.shp')
        m_layer.ConsLayer.assert_called_once_with(fn, providerLib='ogr', source_date = 1)
        building.append.assert_has_calls([
            mock.call(x, query=self.m_app.zone_query),
            mock.call(y, query=self.m_app.zone_query),
            mock.call(z, query=self.m_app.zone_query),
        ])

    @mock.patch('catatom2osm.layer')
    @mock.patch('catatom2osm.csvtools.dict2csv')
    def test_get_building2(self, m_csv, m_layer):
        self.m_app.get_building = get_func(cat.CatAtom2Osm.get_building)
        x = mock.MagicMock()
        y = mock.MagicMock()
        self.m_app.cat.read.side_effect = [x, y, None]
        building = m_layer.ConsLayer.return_value
        self.m_app.get_building(self.m_app)
        building.append.assert_has_calls([
            mock.call(x, query=self.m_app.zone_query),
            mock.call(y, query=self.m_app.zone_query),
        ])

    @mock.patch('catatom2osm.layer')
    @mock.patch('catatom2osm.report')
    def test_process_building1(self, m_report, m_layer):
        m_report.values['max_level'] = {}
        m_report.values['min_level'] = {}
        self.m_app.process_building = get_func(cat.CatAtom2Osm.process_building)
        self.m_app.process_building(self.m_app)
        self.m_app.building.remove_outside_parts.assert_called_once_with()
        self.m_app.building.explode_multi_parts.assert_called_once_with()
        self.m_app.building.clean.assert_called_once_with()
        self.m_app.building.validate.assert_called_once_with(m_report.max_level, m_report.min_level)

    @mock.patch('catatom2osm.report')
    def test_process_building2(self, m_report):
        self.m_app.process_building = get_func(cat.CatAtom2Osm.process_building)
        u = self.m_app.urban_zoning
        r = self.m_app.rustic_zoning
        building = self.m_app.building
        self.m_app.is_new = False
        self.m_app.process_building(self.m_app)
        building.move_address.assert_not_called()
        current_bu_osm = self.m_app.get_current_bu_osm.return_value
        building.conflate.assert_called_once_with(current_bu_osm)
        self.m_app.write_osm.assert_called_once_with(current_bu_osm, 'current_building.osm')
        building.set_tasks.assert_called_once_with(u, r)

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.layer')
    @mock.patch('catatom2osm.report')
    def test_process_tasks(self, m_report, m_layer, m_os):
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.side_effect = [True, True, True, False, True, True]
        m_report.mun_code = 'AAA'
        m_report.mun_name = 'BBB'
        m_report.tasks_m = 10
        task = mock.MagicMock()
        task.featureCount.return_value = 999
        m_layer.ConsLayer.side_effect = [task, task, task, task, task]
        building = mock.MagicMock()
        building.source_date = 1234
        zones = []
        for i in range(5):
            zones.append(mock.MagicMock())
            zones[i].id.return_value = i + 1
        self.m_app.urban_zoning.getFeatures.return_value = [zones[1], zones[3]]
        self.m_app.rustic_zoning.getFeatures.return_value = [
            zones[0], zones[2], zones[4]
        ]
        self.m_app.rustic_zoning.format_label = lambda f: '00' + str(f.id())
        self.m_app.urban_zoning.format_label = lambda f: '0000' + str(f.id())
        self.m_app.process_tasks = get_func(cat.CatAtom2Osm.process_tasks)
        self.m_app.process_tasks(self.m_app, building)
        m_layer.ConsLayer.assert_has_calls([
            mock.call('foo/tasks/missing.shp', 'missing', 'ogr', source_date=1234),
            mock.call('foo/tasks/001.shp', '001', 'ogr', source_date=1234),
            mock.call('foo/tasks/003.shp', '003', 'ogr', source_date=1234),
            mock.call('foo/tasks/00002.shp', '00002', 'ogr', source_date=1234),
            mock.call('foo/tasks/00004.shp', '00004', 'ogr', source_date=1234),
        ])
        comment = setup.changeset_tags['comment'] + ' AAA BBB 00004'
        task.to_osm.assert_called_with(upload='yes', tags={'comment': comment})
        self.assertEqual(self.m_app.merge_address.call_count, 5)
        self.m_app.rustic_zoning.writer.deleteFeatures.assert_called_once_with([5])

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.layer')
    @mock.patch('catatom2osm.report')
    def test_get_tasks(self, m_report, m_layer, m_os):
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.return_value = True
        building = mock.MagicMock()
        building.source_date = 1234
        building.getFeatures.return_value = [
            {'task': '001'}, {'task': '00001'}, {'task': '00001'}
        ]
        building.featureCount.return_value = 3
        building.copy_feature.side_effect = [100, 101, 102]
        m_os.listdir.return_value = ['1', '2', '3']
        m_report.tasks_r = 0
        m_report.tasks_u = 0
        self.m_app.get_tasks = get_func(cat.CatAtom2Osm.get_tasks)
        self.m_app.get_tasks(self.m_app, building)
        m_os.remove.assert_has_calls([
            mock.call('foo/tasks/1'), mock.call('foo/tasks/2'), mock.call('foo/tasks/3')
        ])
        m_layer.ConsLayer.assert_has_calls([
            mock.call('foo/tasks/001.shp', '001', 'ogr', source_date=1234),
            mock.call().writer.addFeatures([100]),
            mock.call('foo/tasks/00001.shp', '00001', 'ogr', source_date=1234),
            mock.call().writer.addFeatures([101, 102])
        ])
        m_os.path.exists.return_value = False
        building.copy_feature.side_effect = [100, 101, 102]
        self.m_app.get_tasks(self.m_app, building)
        self.assertEqual(m_report.tasks_r, 1)
        self.assertEqual(m_report.tasks_u, 1)

    @mock.patch('catatom2osm.layer')
    def test_process_parcel(self, m_layer):
        self.m_app.process_parcel = get_func(cat.CatAtom2Osm.process_parcel)
        self.m_app.process_parcel(self.m_app)
        parcel = m_layer.ParcelLayer.return_value
        parcel_osm = parcel.to_osm.return_value
        self.m_app.write_osm.assert_called_once_with(parcel_osm, "parcel.osm")

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.log')
    @mock.patch('catatom2osm.open')
    @mock.patch('catatom2osm.report')
    def test_end_messages(self, m_report, m_open, m_log, m_os):
        m_os.path.join = lambda *args: '/'.join(args)
        m_fo = mock.MagicMock()
        m_open.return_value = m_fo
        self.m_app.end_messages = get_func(cat.CatAtom2Osm.end_messages)
        self.m_app.is_new = True
        m_report.fixme_count = 3
        self.m_app.end_messages(self.m_app)
        self.assertEqual(m_log.warning.call_args_list[0][0][1], 3)
        self.assertEqual('review.txt', m_log.info.call_args_list[0][0][1])
        self.assertIn('check it', m_log.info.call_args_list[1][0][0])
        self.m_app.fixmes = 0
        self.m_app.is_new = False
        self.m_app.options.tasks = False
        self.m_app.end_messages(self.m_app)
        self.assertEqual(m_log.info.call_args_list[2][0][0], 'Finished!')

    def test_exit(self):
        self.m_app.exit = get_func(cat.CatAtom2Osm.exit)
        self.m_app.test1 = QgsVectorLayer('Point', 'test', 'memory')
        self.m_app.test2 = QgsVectorLayer('Point', 'test', 'memory')
        self.m_app.exit(self.m_app)
        self.assertFalse(hasattr(self.m_app, 'test1'))
        self.assertFalse(hasattr(self.m_app, 'test2'))
        self.m_app.qgs.exitQgis.assert_called_once_with()
        del self.m_app.qgs
        self.m_app.exit(self.m_app)

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.log')
    def test_export_layer(self, m_log, m_os):
        m_os.path.join = lambda *args: '/'.join(args)
        m_layer = mock.MagicMock()
        m_layer.export.return_value = True
        self.m_app.export_layer = get_func(cat.CatAtom2Osm.export_layer)
        self.m_app.export_layer(self.m_app, m_layer, 'bar', 'taz')
        m_layer.export.assert_called_once_with('foo/bar', 'taz', target_crs_id=None)
        output = m_log.info.call_args_list[0][0][0]
        self.assertIn('Generated', output)
        m_layer.export.return_value = False
        with self.assertRaises(IOError):
            self.m_app.export_layer(self.m_app, m_layer, 'bar', 'taz', target_crs_id=None)

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.log')
    @mock.patch('catatom2osm.open')
    @mock.patch('catatom2osm.osmxml')
    @mock.patch('catatom2osm.overpass')
    def test_read_osm(self, m_overpass, m_xml, m_open, m_log, m_os):
        self.m_app.read_osm = get_func(cat.CatAtom2Osm.read_osm)
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.return_value = True
        m_xml.deserialize.return_value.elements = []
        self.m_app.read_osm(self.m_app, 'bar', 'taz')
        m_overpass.Query.assert_not_called()
        m_open.assert_called_with('foo/taz', 'rb')
        m_xml.deserialize.assert_called_once_with(m_open().__enter__())
        output = m_log.warning.call_args_list[0][0][0]
        self.assertIn('No OSM data', output)

        m_xml.deserialize.return_value.elements = [1]
        self.m_app.cat.boundary_search_area = '123456'
        m_os.path.exists.return_value = False
        data = self.m_app.read_osm(self.m_app, 'bar', 'taz')
        m_overpass.Query.assert_called_with('123456')
        m_overpass.Query().add.assert_called_once_with('bar')
        self.assertEqual(data.elements, [1])
        output = m_log.info.call_args_list[0][0][0]
        self.assertIn('Downloading', output)

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.osmxml')
    @mock.patch('catatom2osm.codecs')
    @mock.patch('catatom2osm.io')
    @mock.patch('catatom2osm.gzip')
    def test_write_osm(self, m_gz, m_io, m_codecs, m_xml, m_os):
        m_os.path.join = lambda *args: '/'.join(args)
        m_xml.serialize.return_value = 'taz'
        data = osm.Osm()
        data.Node(0,0, {'ref': '1'})
        data.Node(1,1, {'ref': '2'})
        data.Node(2,2)
        self.m_app.write_osm = get_func(cat.CatAtom2Osm.write_osm)
        self.m_app.write_osm(self.m_app, data, 'bar')
        self.assertNotIn('ref', [k for el in data.elements for k in list(el.tags.keys())])
        m_io.open.assert_called_once_with('foo/bar', 'w', encoding='utf-8')
        file_obj = m_io.open.return_value
        m_xml.serialize.assert_called_once_with(file_obj, data)
        m_xml.reset_mock()
        self.m_app.write_osm(self.m_app, data, 'bar', compress=True)
        m_gz.open.assert_called_once_with('foo/bar.gz', 'w')
        f_gz = m_gz.open.return_value
        m_codecs.getwriter.return_value.assert_called_once_with(f_gz)

    @mock.patch('catatom2osm.layer')
    @mock.patch('catatom2osm.report')
    def test_get_zoning1(self, m_report, m_layer):
        self.m_app.options.zoning = False
        self.m_app.options.tasks = False
        self.m_app.cat.boundary_name = 'foobar'
        m_zoning_gml = mock.MagicMock()
        self.m_app.cat.read.return_value = m_zoning_gml
        m_layer.ZoningLayer.return_value.get_area.return_value = 1
        self.m_app.get_zoning = get_func(cat.CatAtom2Osm.get_zoning)
        self.m_app.get_zoning(self.m_app)
        self.m_app.rustic_zoning.append.assert_called_once_with(
            m_zoning_gml, level='P'
        )
        self.m_app.cat.get_boundary.assert_called_once_with(self.m_app.rustic_zoning)
        self.assertEqual(m_report.mun_name, 'foobar')

    @mock.patch('catatom2osm.layer')
    def test_get_zoning2(self, m_layer):
        self.m_app.options.zoning = True
        m_zoning_gml = mock.MagicMock()
        self.m_app.cat.read.return_value = m_zoning_gml
        mu = mock.MagicMock()
        mr = mock.MagicMock()
        mu.get_area.return_value = 1
        mr.get_area.return_value = 1
        m_layer.ZoningLayer.side_effect = [mu, mr]
        self.m_app.get_zoning = get_func(cat.CatAtom2Osm.get_zoning)
        self.m_app.get_zoning(self.m_app)
        self.m_app.urban_zoning.append.assert_called_once_with(
            m_zoning_gml, level='M'
        )
        self.m_app.urban_zoning.topology()
        self.m_app.urban_zoning.clean_duplicated_nodes_in_polygons()
        self.m_app.urban_zoning.merge_adjacents.called_once_with()
        self.m_app.urban_zoning.set_tasks.called_once_with()
        self.m_app.rustic_zoning.set_tasks.called_once_with()

    @mock.patch('catatom2osm.layer')
    @mock.patch('catatom2osm.report')
    def test_read_address(self, m_report, m_layer):
        self.m_app.read_address = get_func(cat.CatAtom2Osm.read_address)
        self.m_app.cat.read.return_value.fieldNameIndex.return_value = 0
        m_layer.AddressLayer.return_value.translate_field.return_value = 1
        self.m_app.read_address(self.m_app)
        self.m_app.address.append.assert_called_once_with(
            self.m_app.cat.read(), query=self.m_app.zone_query
        )
        self.m_app.address.append.reset_mock()
        self.m_app.cat.read.return_value.writer.fieldNameIndex.return_value = -1
        with self.assertRaises(IOError):
            self.m_app.read_address(self.m_app)
        self.m_app.cat.read.return_value.writer.fieldNameIndex.side_effect = [-1, 0]
        self.m_app.read_address(self.m_app)
        self.m_app.address.append.assert_called_once_with(
            self.m_app.cat.read(), query=self.m_app.zone_query
        )

    @mock.patch('catatom2osm.cdau')
    def test_get_auxiliary_addresses(self, m_cdau):
        self.m_app.cat.zip_code = '29900'
        self.m_app.path = os.path.join('/foo', 'bar')
        self.m_app.get_auxiliary_addresses = get_func(cat.CatAtom2Osm.get_auxiliary_addresses)
        self.m_app.get_auxiliary_addresses(self.m_app)
        m_cdau.Reader.assert_called_once_with(os.path.join('/foo', setup.aux_path))

    @mock.patch('catatom2osm.report')
    def test_merge_address(self, m_report):
        address = osm.Osm()
        address.Node(0,0, {'ref': '1', 'addr:street': 'address1', 'image': 'foo'})
        address.Node(2,0, {'ref': '2', 'addr:street': 'address2', 'entrance': 'yes', 'image': 'bar'})
        address.Node(4,0, {'ref': '3', 'addr:street': 'address3', 'entrance': 'yes'})
        address.Node(6,0, {'ref': '4', 'addr:place': 'address5', 'entrance': 'yes'})
        building = osm.Osm()
        w0 = building.Way([], {'ref': '0'}) # building with ref not in address
        # no entrance address, tags to way
        w1 = building.Way([(0,0), (1,0), (1,1), (0,0)], {'ref': '1'})
        # entrance exists, tags to node
        n2 = building.Node(2,0)
        w2 = building.Way([n2, (3,0), (3,1), (2,0)], {'ref': '2'})
        # entrance don't exists, tags to way
        w3 = building.Way([(4,1), (5,0), (5,1), (4,1)], {'ref': '3'})
        # entrance exists, tags to node in relation
        n5 = building.Node(6,0)
        w6 = building.Way([(6,5), (9,5), (9,8), (6,8), (6,5)])
        w7 = building.Way([n5, (9,0), (9,3), (6,3), (6,0)])
        w8 = building.Way([(7,1), (8,1), (8,2), (7,2), (7,1)])
        r1 = building.Relation(tags = {'ref': '4'})
        r1.append(w6, 'outer')
        r1.append(w7, 'outer')
        r1.append(w8, 'inner')
        self.m_app.merge_address = get_func(cat.CatAtom2Osm.merge_address)
        self.m_app.merge_address(self.m_app, building, address)
        self.assertNotIn('addrtags', w0.tags)
        self.assertEqual(w1.tags['addr:street'], 'address1')
        self.assertNotIn('image', w1.tags)
        self.assertEqual(n2.tags['addr:street'], 'address2')
        self.assertNotIn('image', n2.tags)
        self.assertEqual(w3.tags['addr:street'], 'address3')
        self.assertNotIn('addr:street', [k for n in w3.nodes for k in list(n.tags.keys())])
        self.assertEqual(n5.tags['addr:place'], 'address5')
        address.tags['source:date'] = 'foobar'
        self.m_app.merge_address(self.m_app, building, address)
        self.assertEqual(building.tags['source:date:addr'], address.tags['source:date'])

    @mock.patch('catatom2osm.os')
    @mock.patch('catatom2osm.csvtools')
    def test_get_translations(self, m_csv, m_os):
        self.m_app.get_translations = get_func(cat.CatAtom2Osm.get_translations)
        setup.app_path = 'bar'
        m_os.path.join = lambda *args: '/'.join(args)
        m_csv.csv2dict.return_value = {'RAZ': ' raz '}
        m_os.path.exists.return_value = True
        address = mock.MagicMock()
        names = self.m_app.get_translations(self.m_app, address)
        m_csv.dict2csv.assert_not_called()
        m_csv.csv2dict.assert_has_calls([
            mock.call('bar/highway_types.csv', setup.highway_types),
            mock.call('foo/highway_names.csv', {}),
        ])
        self.assertEqual(names, {'RAZ': 'raz'})
        address.get_highway_names.return_value = {'TAZ': ' taz '}
        m_csv.csv2dict.reset_mock()
        m_os.path.exists.return_value = False
        self.m_app.is_new = True
        names = self.m_app.get_translations(self.m_app, address)
        address.get_highway_names.assert_called_once_with(self.m_app.get_highway.return_value)
        m_csv.csv2dict.assert_not_called()
        m_csv.dict2csv.assert_has_calls([
            mock.call('bar/highway_types.csv', setup.highway_types),
            mock.call('foo/highway_names.csv', {'TAZ': 'taz'}, sort=1),
        ])
        self.assertEqual(names, {'TAZ': 'taz'})
        self.m_app.options.manual = True
        names = self.m_app.get_translations(self.m_app, address)
        address.get_highway_names.assert_called_with(None)

    @mock.patch('catatom2osm.layer')
    def test_get_highway(self, m_layer):
        self.m_app.read_osm.return_value = 1234
        self.m_app.get_highway = get_func(cat.CatAtom2Osm.get_highway)
        h = self.m_app.get_highway(self.m_app)
        h.read_from_osm.assert_called_once_with(1234)

    def test_get_current_bu_osm(self):
        self.m_app.get_current_bu_osm = get_func(cat.CatAtom2Osm.get_current_bu_osm)
        self.m_app.read_osm.return_value = 1234
        c = self.m_app.get_current_bu_osm(self.m_app)
        self.assertEqual(c, 1234)

    @mock.patch('catatom2osm.log')
    @mock.patch('catatom2osm.report')
    def test_get_current_ad_osm(self, m_report, m_log):
        d = osm.Osm()
        d.Node(0,0, {'addr:housenumber': '12', 'addr:street': 'foobar'})
        d.Node(1,1, {'addr:housenumber': '14', 'addr:street': 'foobar'})
        d.Node(2,2, {'addr:housenumber': '10', 'addr:place': 'bartaz'})
        self.m_app.get_current_ad_osm = get_func(cat.CatAtom2Osm.get_current_ad_osm)
        self.m_app.read_osm.return_value = d
        address = self.m_app.get_current_ad_osm(self.m_app)
        self.assertEqual(address, set(['foobar14', 'foobar12', 'bartaz10']))
        self.assertNotIn('osm_addresses_whithout_number', m_report)
        d.Node(3,3, {'addr:street': 'x'})
        d.Node(4,4, {'addr:place': 'y'})
        self.m_app.read_osm.return_value = d
        address = self.m_app.get_current_ad_osm(self.m_app)
        self.assertEqual(m_report.osm_addresses_whithout_number, 2)
