import logging
import os
import unittest
from importlib import reload
from optparse import Values

import mock
from past.builtins import basestring
from qgis.core import QgsVectorLayer

from catatom2osm import app, config, osm

qgs = app.QgsSingleton()
os.environ['LANGUAGE'] = 'C'
config.install_gettext('catato2osm', '')
m_log = mock.MagicMock()
m_log.app_level = logging.INFO


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
    def test_run_default(self):
        self.m_app.source = 'building'
        self.m_app.building = mock.MagicMock()
        self.m_app.is_new = True
        self.m_app.options.address = True
        self.m_app.run = get_func(app.CatAtom2Osm.run)
        self.m_app.run(self.m_app)
        self.m_app.stop_address.assert_called_once_with()

    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    def test_run_default_2nd(self):
        self.m_app.is_new = False
        self.m_app.options.address = True
        self.m_app.source = 'building'
        self.m_app.run = get_func(app.CatAtom2Osm.run)
        self.m_app.run(self.m_app)
        self.m_app.resume_address.assert_called_once_with()
        self.m_app.process_tasks.assert_called_once_with(self.m_app.building)

    @mock.patch('catatom2osm.app.log', m_log)
    @mock.patch('catatom2osm.app.geo', mock.MagicMock())
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

    @mock.patch('catatom2osm.app.log', m_log)
    @mock.patch('catatom2osm.app.report', mock.MagicMock())
    def test_process_building_no_add_no_conf(self):
        self.m_app.process_building = get_func(app.CatAtom2Osm.process_building)
        self.m_app.options.address = False
        self.m_app.options.manual = True
        self.m_app.process_building(self.m_app)
        self.m_app.building.move_address.assert_not_called()

    @mock.patch('catatom2osm.app.report')
    def test_process_tasks(self, m_report):
        self.m_app.get_tasks.return_value = {
            '123456A': mock.MagicMock(),
            '123456B': mock.MagicMock(),
            '123456C': mock.MagicMock(),
            '123456D': mock.MagicMock(),
            '123456E': mock.MagicMock(),
        }
        building = mock.MagicMock()
        building.source_date = 1234
        self.m_app.parcel.getFeatures.return_value = [
            {'localId': '123456E', 'zone': '001'},
            {'localId': '123456C', 'zone': '002'},
            {'localId': '123456D', 'zone': '00001'},
            {'localId': '123456B', 'zone': '00002'},
            {'localId': '123456A', 'zone': '00003'},
        ]
        self.m_app.get_task_comment = lambda x: 'X' + x
        self.m_app.process_tasks = get_func(app.CatAtom2Osm.process_tasks)
        self.m_app.process_tasks(self.m_app, building)
        for label, task in self.m_app.get_tasks.return_value.items():
            task.to_osm.assert_called_with(
                upload='yes', tags={'comment': 'X' + label}
            )
        self.assertEqual(self.m_app.merge_address.call_count, 5)

    @mock.patch('catatom2osm.app.os')
    @mock.patch('catatom2osm.app.type')
    @mock.patch('catatom2osm.app.report')
    def test_get_tasks(self, m_report, m_type, m_os):
        m_os.path.join = lambda *args: '/'.join(args)
        m_os.listdir.return_value = ['1', '2', '3']
        layer_class = mock.MagicMock()
        m_type.return_value = layer_class
        self.m_app.tasks = {'00001': '00001', '00002': '00001'}
        building = mock.MagicMock()
        building.get_id = lambda feat: feat['localId']
        building.getFeatures.return_value = [
            {'localId': '001'}, {'localId': '00001'}, {'localId': '00002'}
        ]
        building.featureCount.return_value = 3
        building.copy_feature.side_effect = [100, 101, 102]
        self.m_app.get_tasks = get_func(app.CatAtom2Osm.get_tasks)
        self.m_app.get_tasks(self.m_app, building)
        m_os.remove.assert_has_calls([
            mock.call('33333/tasks/1'),
            mock.call('33333/tasks/2'),
            mock.call('33333/tasks/3'),
        ])
        layer_class.assert_has_calls([
            mock.call(baseName='001'),
            mock.call().writer.addFeatures([100]),
            mock.call(baseName='00001'),
            mock.call().writer.addFeatures([101, 102])
        ])

    @mock.patch('catatom2osm.app.geo')
    def test_process_parcel(self, m_layer):
        self.m_app.tasks = {'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd', 'e': 'e'}
        self.m_app.parcel.merge_by_adjacent_buildings.return_value = {'b': 'a', 'c': 'a'}
        self.m_app.parcel.merge_by_parts_count.return_value = {'e': 'd'}
        self.m_app.process_parcel = get_func(app.CatAtom2Osm.process_parcel)
        self.m_app.process_parcel(self.m_app)
        result = {'a': 'a', 'b': 'a', 'c': 'a', 'd': 'd', 'e': 'd'}
        self.assertEqual(self.m_app.tasks, result)

    @mock.patch('catatom2osm.geo.layer.base.log', m_log)
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

    @mock.patch('catatom2osm.app.geo')
    def test_get_highway(self, m_layer):
        self.m_app.read_osm.return_value = 1234
        self.m_app.get_highway = get_func(app.CatAtom2Osm.get_highway)
        h = self.m_app.get_highway(self.m_app)
        h.read_from_osm.assert_called_once_with(1234)

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
        self.assertEqual(m_report.osm_addresses_without_number, 2)

