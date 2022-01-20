from past.builtins import basestring
from importlib import reload
import mock
import unittest
import os
from optparse import Values
from qgis.core import QgsVectorLayer

from catatom2osm import config, osm, app
qgs = app.QgsSingleton()
os.environ['LANGUAGE'] = 'C'
config.install_gettext('catato2osm', '')


def get_func(f):
    return getattr(f, '__func__', f)


class TestQgsSingleton(unittest.TestCase):

    @mock.patch('catatom2osm.app.QgsSingleton._qgs', None)
    @mock.patch('catatom2osm.app.gdal')
    @mock.patch('catatom2osm.app.QgsApplication')
    def test_new(self, m_qgsapp, m_gdal):
        q1 = app.QgsSingleton()
        self.assertEqual(m_qgsapp.call_count, 1)
        m_gdal.SetConfigOption.assert_has_calls([
            mock.call('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES'),
            mock.call('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        ])
        q2 = app.QgsSingleton()
        self.assertEqual(m_qgsapp.call_count, 1)
        self.assertTrue(q1 is q2)


class TestCatAtom2Osm(unittest.TestCase):

    def setUp(self):
        options = {
            'building': True, 'tasks': True, 'list_zones': False,
            'log_level': 'INFO', 'list': '', 'zoning': False, 'version': False,
            'address': True, 'manual': False, 'zone': [], 'task': ['33333'],
            'comment': False, 'split': None, 'args': '33333',
        }
        self.m_app = mock.MagicMock()
        self.m_app.options = Values(options)
        self.m_app.get_translations.return_value = ([], False)
        self.m_app.path = '33333'
        self.m_app.highway_names_path = '33333/highway_names.csv'
        self.m_app.zone = self.m_app.options.zone
        self.m_app.tasks_path = '33333/tasks'
        self.m_app.is_new = False
        self.m_app.cat.get_path = (
            lambda *args: self.m_app.path + '/' + '/'.join(args)
        )

    @mock.patch('catatom2osm.catatom.Reader')
    @mock.patch('catatom2osm.app.report')
    @mock.patch('catatom2osm.app.os')
    def test_init(self, m_os, m_report, m_cat):
        m_cat.return_value.get_path = lambda x: 'foo/' + x
        m_os.path.exists.return_value = False
        self.m_app.init = get_func(app.CatAtom2Osm.__init__)
        self.m_app.init(self.m_app, 'xxx/12345', self.m_app.options)
        m_cat.assert_called_once_with('xxx/12345')
        self.assertEqual(self.m_app.path, m_cat().path)
        m_os.makedirs.assert_called_once_with('foo/tasks')

    @mock.patch('catatom2osm.app.gdal')
    def test_gdal(self, m_gdal):
        reload(app)
        self.assertFalse(m_gdal.PushErrorHandler.called)
        config.silence_gdal = True
        reload(app)
        m_gdal.PushErrorHandler.called_once_with('CPLQuietErrorHandler')

    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    def test_run_list(self):
        self.m_app.run = get_func(app.CatAtom2Osm.run)
        self.m_app.options.list_zones = True
        self.m_app.run(self.m_app)
        self.m_app.list_zones.assert_called_once_with()
        self.m_app.get_zoning.assert_not_called()

    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    def test_run_default(self):
        self.m_app.run = get_func(app.CatAtom2Osm.run)
        llayer = self.m_app.labels_layer
        address = self.m_app.address
        self.m_app.building.conflate.return_value = False
        self.m_app.run(self.m_app)
        self.m_app.process_tasks.assert_called_once_with(llayer)
        self.m_app.process_building.assert_called_once_with()
        self.m_app.read_address.assert_called_once_with()
        address.to_osm.assert_called_once_with()

    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    def test_run_default_new(self):
        self.m_app.is_new = True
        self.m_app.run = get_func(app.CatAtom2Osm.run)
        self.m_app.run(self.m_app)
        self.m_app.process_zoning.assert_not_called()
        self.m_app.process_tasks.assert_not_called()
        self.m_app.process_building.assert_not_called()

    @mock.patch('catatom2osm.app.layer')
    def test_get_building(self, m_layer):
        self.m_app.get_building = get_func(app.CatAtom2Osm.get_building)
        bugml = mock.MagicMock()
        bugml.source_date = 1
        partgml = mock.MagicMock()
        othergml = mock.MagicMock()
        self.m_app.cat.read.side_effect = [bugml, partgml, othergml]
        building = m_layer.ConsLayer.return_value
        self.m_app.get_building(self.m_app)
        fn = os.path.join('33333', 'building.shp')
        m_layer.ConsLayer.assert_called_once_with(
            fn, providerLib='ogr', source_date = 1
        )
        building.append.assert_has_calls([
            mock.call(bugml, query=self.m_app.zone_query),
            mock.call(partgml, query=self.m_app.zone_query),
            mock.call(othergml, query=self.m_app.zone_query),
        ])

    @mock.patch('catatom2osm.app.layer')
    def test_get_building_no_other(self, m_layer):
        self.m_app.get_building = get_func(app.CatAtom2Osm.get_building)
        bugml = mock.MagicMock()
        partgml = mock.MagicMock()
        self.m_app.cat.read.side_effect = [bugml, partgml, None]
        building = m_layer.ConsLayer.return_value
        self.m_app.get_building(self.m_app)
        building.append.assert_has_calls([
            mock.call(bugml, query=self.m_app.zone_query),
            mock.call(partgml, query=self.m_app.zone_query),
        ])

    @mock.patch('catatom2osm.app.layer', mock.MagicMock())
    @mock.patch('catatom2osm.app.report')
    def test_process_building(self, m_report):
        m_report.values['max_level'] = {}
        m_report.values['min_level'] = {}
        self.m_app.process_building = get_func(app.CatAtom2Osm.process_building)
        self.m_app.process_building(self.m_app)
        building = self.m_app.building
        building.remove_outside_parts.assert_called_once_with()
        building.explode_multi_parts.assert_called_once_with()
        building.clean.assert_called_once_with()
        building.validate.assert_called_once()
        building.move_address.assert_called_once_with(self.m_app.address)
        current_bu_osm = self.m_app.get_current_bu_osm.return_value
        building.conflate.assert_called_once_with(current_bu_osm)
        building.set_tasks.assert_called_once_with()

    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    def test_process_building_no_add_no_conf(self):
        self.m_app.process_building = get_func(app.CatAtom2Osm.process_building)
        self.m_app.options.address = False
        self.m_app.options.manual = True
        self.m_app.process_building(self.m_app)
        self.m_app.building.move_address.assert_not_called()
        self.m_app.building.conflate.assert_not_called()

    @mock.patch('catatom2osm.app.os')
    @mock.patch('catatom2osm.app.layer')
    @mock.patch('catatom2osm.app.report')
    def test_process_tasks(self, m_report, m_layer, m_os):
        m_os.path.exists.side_effect = [True, True, False, True, True, True]
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
        self.m_app.urban_zoning.search.return_value = [zones[1], zones[3]]
        self.m_app.rustic_zoning.search.return_value = [
            zones[0], zones[2], zones[4]
        ]
        self.m_app.rustic_zoning.format_label = lambda f: '00' + str(f.id())
        self.m_app.urban_zoning.format_label = lambda f: '0000' + str(f.id())
        self.m_app.process_tasks = get_func(app.CatAtom2Osm.process_tasks)
        self.m_app.process_tasks(self.m_app, building)
        m_layer.ConsLayer.assert_has_calls([
            mock.call('33333/tasks/001.shp', '001', 'ogr', source_date=1234),
            mock.call('33333/tasks/003.shp', '003', 'ogr', source_date=1234),
            mock.call('33333/tasks/00002.shp', '00002', 'ogr', source_date=1234),
            mock.call('33333/tasks/00004.shp', '00004', 'ogr', source_date=1234),
            mock.call('33333/tasks/missing.shp', 'missing', 'ogr', source_date=1234),
        ])
        comment = config.changeset_tags['comment'] + ' AAA BBB missing'
        task.to_osm.assert_called_with(upload='yes', tags={'comment': comment})
        self.assertEqual(self.m_app.merge_address.call_count, 5)
        self.m_app.rustic_zoning.writer.deleteFeatures.assert_called_once_with([5])

    @mock.patch('catatom2osm.app.os')
    @mock.patch('catatom2osm.app.layer')
    @mock.patch('catatom2osm.app.report')
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
        self.m_app.get_tasks = get_func(app.CatAtom2Osm.get_tasks)
        self.m_app.get_tasks(self.m_app, building)
        m_os.remove.assert_has_calls([
            mock.call('33333/tasks/1'),
            mock.call('33333/tasks/2'),
            mock.call('33333/tasks/3'),
        ])
        m_layer.ConsLayer.assert_has_calls([
            mock.call('33333/tasks/001.shp', '001', 'ogr', source_date=1234),
            mock.call().writer.addFeatures([100]),
            mock.call('33333/tasks/00001.shp', '00001', 'ogr', source_date=1234),
            mock.call().writer.addFeatures([101, 102])
        ])
        m_os.path.exists.return_value = False
        building.copy_feature.side_effect = [100, 101, 102]
        self.m_app.get_tasks(self.m_app, building)
        self.assertEqual(m_report.tasks_r, 1)
        self.assertEqual(m_report.tasks_u, 1)

    @mock.patch('catatom2osm.app.layer')
    def test_process_parcel(self, m_layer):
        self.m_app.process_parcel = get_func(app.CatAtom2Osm.process_parcel)
        self.m_app.process_parcel(self.m_app)
        parcel = m_layer.ParcelLayer.return_value
        parcel_osm = parcel.to_osm.return_value
        self.m_app.write_osm.assert_called_once_with(parcel_osm, "parcel.osm")

    @mock.patch('catatom2osm.app.os', mock.MagicMock())
    @mock.patch('catatom2osm.app.log')
    @mock.patch('catatom2osm.app.open')
    @mock.patch('catatom2osm.app.report')
    def test_end_messages(self, m_report, m_open, m_log):
        m_fo = mock.MagicMock()
        m_open.return_value = m_fo
        self.m_app.end_messages = get_func(app.CatAtom2Osm.end_messages)
        self.m_app.is_new = True
        m_report.fixme_count = 3
        self.m_app.end_messages(self.m_app)
        self.assertEqual(m_log.warning.call_args_list[0][0][1], 3)
        self.assertEqual('review.txt', m_log.info.call_args_list[0][0][1])
        self.assertIn('check it', m_log.info.call_args_list[1][0][0])
        m_report.cons_end_stats.assert_called_once()
        self.assertIn('Generated', m_log.info.call_args_list[1][0][0])

    @mock.patch('catatom2osm.app.os', mock.MagicMock())
    @mock.patch('catatom2osm.app.log')
    @mock.patch('catatom2osm.app.open')
    @mock.patch('catatom2osm.app.report')
    def test_end_messages_finish(self, m_report, m_open, m_log):
        self.m_app.end_messages = get_func(app.CatAtom2Osm.end_messages)
        self.m_app.options.building = False
        m_report.fixme_stats.return_value = False
        self.m_app.end_messages(self.m_app)
        m_log.warning.assert_not_called()
        m_report.cons_end_stats.assert_not_called()
        m_log.info.assert_called_once_with('Finished!')

    def test_exit(self):
        self.m_app.exit = get_func(app.CatAtom2Osm.exit)
        self.m_app.test1 = QgsVectorLayer('Point', 'test', 'memory')
        self.m_app.test2 = QgsVectorLayer('Point', 'test', 'memory')
        self.m_app.exit(self.m_app)
        self.assertFalse(hasattr(self.m_app, 'test1'))
        self.assertFalse(hasattr(self.m_app, 'test2'))
        del self.m_app.qgs
        self.m_app.exit(self.m_app)

    @mock.patch('catatom2osm.app.os')
    @mock.patch('catatom2osm.app.log')
    def test_export_layer(self, m_log, m_os):
        m_layer = mock.MagicMock()
        m_layer.export.return_value = True
        self.m_app.export_layer = get_func(app.CatAtom2Osm.export_layer)
        self.m_app.export_layer(self.m_app, m_layer, 'bar', 'taz')
        m_layer.export.assert_called_once_with('33333/bar', 'taz', target_crs_id=None)
        output = m_log.info.call_args_list[0][0][0]
        self.assertIn('Generated', output)
        m_layer.export.return_value = False
        with self.assertRaises(IOError):
            self.m_app.export_layer(self.m_app, m_layer, 'bar', 'taz', target_crs_id=None)

    @mock.patch('catatom2osm.app.os')
    @mock.patch('catatom2osm.app.log')
    @mock.patch('catatom2osm.app.open')
    @mock.patch('catatom2osm.app.osmxml')
    @mock.patch('catatom2osm.app.overpass')
    def test_read_osm(self, m_overpass, m_xml, m_open, m_log, m_os):
        self.m_app.read_osm = get_func(app.CatAtom2Osm.read_osm)
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.return_value = True
        m_xml.deserialize.return_value.elements = []
        self.m_app.read_osm(self.m_app, 'bar', 'taz')
        m_overpass.Query.assert_not_called()
        m_open.assert_called_with('33333/bar/taz', 'rb')
        m_xml.deserialize.assert_called_once_with(m_open())
        output = m_log.warning.call_args_list[0][0][0]
        self.assertIn('No OSM data', output)
        m_xml.deserialize.return_value.elements = [1]
        self.m_app.boundary_search_area = '123456'
        m_os.path.exists.return_value = False
        data = self.m_app.read_osm(self.m_app, 'taz', ql='bar')
        m_overpass.Query.assert_called_with('123456')
        m_overpass.Query().add.assert_called_once_with('bar')
        self.assertEqual(data.elements, [1])
        output = m_log.info.call_args_list[0][0][0]
        self.assertIn('Downloading', output)

    @mock.patch('catatom2osm.app.os')
    @mock.patch('catatom2osm.app.osmxml')
    @mock.patch('catatom2osm.app.codecs')
    @mock.patch('catatom2osm.app.io')
    @mock.patch('catatom2osm.app.gzip')
    def test_write_osm(self, m_gz, m_io, m_codecs, m_xml, m_os):
        m_xml.serialize.return_value = 'taz'
        data = osm.Osm()
        data.Node(0,0, {'ref': '1'})
        data.Node(1,1, {'ref': '2'})
        data.Node(2,2)
        self.m_app.write_osm = get_func(app.CatAtom2Osm.write_osm)
        self.m_app.write_osm(self.m_app, data, 'bar')
        self.assertNotIn('ref', [k for el in data.elements for k in list(el.tags.keys())])
        m_io.open.assert_called_once_with('33333/bar', 'w', encoding='utf-8')
        file_obj = m_io.open.return_value
        m_xml.serialize.assert_called_once_with(file_obj, data)
        m_xml.reset_mock()
        self.m_app.write_osm(self.m_app, data, 'bar.gz')
        m_gz.open.assert_called_once_with('33333/bar.gz', 'w')
        f_gz = m_gz.open.return_value
        m_codecs.getwriter.return_value.assert_called_once_with(f_gz)

    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    @mock.patch('catatom2osm.app.layer')
    def test_get_zoning1(self, m_layer):
        self.m_app.options.zoning = False
        self.m_app.options.tasks = False
        m_zoning_gml = mock.MagicMock()
        self.m_app.cat.read.return_value = m_zoning_gml
        mu = mock.MagicMock()
        mr = mock.MagicMock()
        mu.get_area.return_value = 1
        mr.get_area.return_value = 1
        m_layer.ZoningLayer.side_effect = [mu, mr]
        self.m_app.get_zoning = get_func(app.CatAtom2Osm.get_zoning)
        self.m_app.get_zoning(self.m_app)
        self.m_app.rustic_zoning.append.assert_called_once_with(
            m_zoning_gml, level='P'
        )
        self.m_app.urban_zoning.append.assert_called_once_with(
            m_zoning_gml, level='M'
        )

    @mock.patch('catatom2osm.app.layer')
    @mock.patch('catatom2osm.app.report')
    def test_read_address(self, m_report, m_layer):
        self.m_app.read_address = get_func(app.CatAtom2Osm.read_address)
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

    @mock.patch('catatom2osm.app.cdau')
    def test_get_auxiliary_addresses(self, m_cdau):
        self.m_app.cat.zip_code = '29900'
        self.m_app.path = os.path.join('/foo', 'bar')
        self.m_app.get_auxiliary_addresses = get_func(app.CatAtom2Osm.get_auxiliary_addresses)
        self.m_app.get_auxiliary_addresses(self.m_app)
        m_cdau.Reader.assert_called_once_with(os.path.join('/foo', config.aux_path))

    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    def test_merge_address(self):
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
        self.m_app.merge_address = get_func(app.CatAtom2Osm.merge_address)
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

    @mock.patch('catatom2osm.app.os')
    @mock.patch('catatom2osm.app.csvtools')
    def test_get_translations(self, m_csv, m_os):
        m_os.path.join = lambda *args: '/'.join(args)
        self.m_app.get_translations = get_func(app.CatAtom2Osm.get_translations)
        config.app_path = 'foo'
        m_csv.csv2dict.return_value = {'RAZ': ' raz '}
        m_os.path.exists.return_value = True
        address = mock.MagicMock()
        names = self.m_app.get_translations(self.m_app, address)
        m_csv.dict2csv.assert_not_called()
        m_csv.csv2dict.assert_has_calls([
            mock.call('foo/highway_types.csv', config.highway_types),
            mock.call('33333/highway_names.csv', {}),
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
            mock.call('foo/highway_types.csv', config.highway_types),
            mock.call('33333/highway_names.csv', {'TAZ': 'taz'}, sort=1),
        ])
        self.assertEqual(names, {'TAZ': 'taz'})
        self.m_app.options.manual = True
        names = self.m_app.get_translations(self.m_app, address)
        address.get_highway_names.assert_called_with(None)

    @mock.patch('catatom2osm.app.layer')
    def test_get_highway(self, m_layer):
        self.m_app.read_osm.return_value = 1234
        self.m_app.get_highway = get_func(app.CatAtom2Osm.get_highway)
        h = self.m_app.get_highway(self.m_app)
        h.read_from_osm.assert_called_once_with(1234)

    def test_get_current_bu_osm(self):
        self.m_app.get_current_bu_osm = get_func(app.CatAtom2Osm.get_current_bu_osm)
        self.m_app.read_osm.return_value = 1234
        c = self.m_app.get_current_bu_osm(self.m_app)
        self.assertEqual(c, 1234)

    @mock.patch('catatom2osm.app.log')
    @mock.patch('catatom2osm.app.report')
    def test_get_current_ad_osm(self, m_report, m_log):
        d = osm.Osm()
        d.Node(0,0, {'addr:housenumber': '12', 'addr:street': 'foobar'})
        d.Node(1,1, {'addr:housenumber': '14', 'addr:street': 'foobar'})
        d.Node(2,2, {'addr:housenumber': '10', 'addr:place': 'bartaz'})
        self.m_app.get_current_ad_osm = get_func(app.CatAtom2Osm.get_current_ad_osm)
        self.m_app.read_osm.return_value = d
        address = self.m_app.get_current_ad_osm(self.m_app)
        self.assertEqual(address, set(['foobar14', 'foobar12', 'bartaz10']))
        self.assertNotIn('osm_addresses_whithout_number', m_report)
        d.Node(3,3, {'addr:street': 'x'})
        d.Node(4,4, {'addr:place': 'y'})
        self.m_app.read_osm.return_value = d
        address = self.m_app.get_current_ad_osm(self.m_app)
        self.assertEqual(m_report.osm_addresses_whithout_number, 2)

    @mock.patch('catatom2osm.app.layer')
    def test_split_zoning(self, m_layer):
        f = lambda x: {'label': x}
        self.m_app.zone = [1, 2, 3]
        self.m_app.rustic_zoning.getFeatures.return_value = [f(3), f(4), f(5)]
        self.m_app.urban_zoning.getFeatures.return_value = [f(2), f(6), f(7)]
        self.m_app.split_zoning = get_func(app.CatAtom2Osm.split_zoning)
        self.m_app.split_zoning(self.m_app)
        self.assertEqual(self.m_app.zone, [1, 2, 3, 4, 5, 6, 7])
