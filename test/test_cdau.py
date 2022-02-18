import os
import unittest

import mock

from catatom2osm import cdau, config, geo
from catatom2osm.app import QgsSingleton

qgs = QgsSingleton()
os.environ['LANGUAGE'] = 'C'
config.install_gettext('catato2osm', '')


def get_func(f):
    return getattr(f, '__func__', f)

class TestCdau(unittest.TestCase):

    def setUp(self):
        self.m_cdau = mock.MagicMock()

    def test_cod_mun_cat2ine(self):
        self.assertEqual(cdau.cod_mun_cat2ine('04030'), '04030')
        self.assertEqual(cdau.cod_mun_cat2ine('04040'), '04901')
        self.assertEqual(cdau.cod_mun_cat2ine('04103'), '04103')
        self.assertEqual(cdau.cod_mun_cat2ine('04104'), '04902')
        self.assertEqual(cdau.cod_mun_cat2ine('14900'), '14021')
        self.assertEqual(cdau.cod_mun_cat2ine('18059'), '18907')
        self.assertEqual(cdau.cod_mun_cat2ine('18002'), '18001')
        self.assertEqual(cdau.cod_mun_cat2ine('18062'), '18061')
        self.assertEqual(cdau.cod_mun_cat2ine('18063'), '18119')
        self.assertEqual(cdau.cod_mun_cat2ine('18064'), '18062')
        self.assertEqual(cdau.cod_mun_cat2ine('18119'), '18117')
        self.assertEqual(cdau.cod_mun_cat2ine('18120'), '18903')
        self.assertEqual(cdau.cod_mun_cat2ine('18121'), '18120')
        self.assertEqual(cdau.cod_mun_cat2ine('18135'), '18134')
        self.assertEqual(cdau.cod_mun_cat2ine('18137'), '18135')
        self.assertEqual(cdau.cod_mun_cat2ine('18142'), '18140')
        self.assertEqual(cdau.cod_mun_cat2ine('18144'), '18141')
        self.assertEqual(cdau.cod_mun_cat2ine('18183'), '18180')
        self.assertEqual(cdau.cod_mun_cat2ine('18185'), '18181')
        self.assertEqual(cdau.cod_mun_cat2ine('18198'), '18194')
        self.assertEqual(cdau.cod_mun_cat2ine('18199'), '18912')
        self.assertEqual(cdau.cod_mun_cat2ine('21001'), '21001')
        self.assertEqual(cdau.cod_mun_cat2ine('21059'), '21059')
        self.assertEqual(cdau.cod_mun_cat2ine('21060'), '21061')
        self.assertEqual(cdau.cod_mun_cat2ine('21079'), '21060')
        self.assertEqual(cdau.cod_mun_cat2ine('21900'), '21041')
        self.assertEqual(cdau.cod_mun_cat2ine('29900'), '29067')

    @mock.patch('catatom2osm.cdau.os')
    def test_init(self, m_os):
        self.m_cdau.init = get_func(cdau.Reader.__init__)
        m_os.path.exists.return_value = True
        m_os.path.isdir.return_value = False
        with self.assertRaises(IOError) as cm:
            self.m_cdau.init(self.m_cdau, 'foobar')
        self.assertIn('Not a directory', str(cm.exception))
        m_os.makedirs.assert_not_called()
        m_os.path.exists.return_value = False
        m_os.path.isdir.return_value = True
        self.m_cdau.init(self.m_cdau, 'foobar')
        m_os.makedirs.assert_called_with('foobar')

    @mock.patch('catatom2osm.cdau.os')
    @mock.patch('catatom2osm.cdau.geo')
    @mock.patch('catatom2osm.cdau.download')
    def test_read(self, m_download, m_layer, m_os):
        self.m_cdau.read = get_func(cdau.Reader.read)
        with self.assertRaises(ValueError) as cm:
            self.m_cdau.read(self.m_cdau, '38')
        self.assertIn('Province code', str(cm.exception))

        m_os.path.join = lambda *args: '/'.join(args)
        m_os.path.exists.return_value = True
        self.m_cdau.path = 'foobar'
        self.m_cdau.src_date = 'taz'
        csv = mock.MagicMock()
        csv.isValid.return_value = True
        m_layer.BaseLayer.return_value = csv
        self.assertEqual(self.m_cdau.read(self.m_cdau, '29'), csv)
        m_download.wget.assert_not_called()
        self.assertEqual(csv.source_date, 'taz')

        m_os.path.exists.return_value = False
        csv.isValid.return_value = False
        with self.assertRaises(IOError) as cm:
            self.m_cdau.read(self.m_cdau, '29')
        self.assertIn('Failed to load layer', str(cm.exception))
        fn = cdau.csv_name.format('Malaga')
        url = cdau.cdau_url.format(fn)
        m_download.wget.assert_called_once_with(url, 'foobar/'+fn)

    @mock.patch('catatom2osm.cdau.os')
    @mock.patch('catatom2osm.cdau.open')
    @mock.patch('catatom2osm.cdau.download')
    def test_get_metadata(self, m_download, m_open, m_os):
        resp = mock.MagicMock()
        resp.text = '<p> La fecha de referencia de los datos de cada uno de los ficheros es el 5 de marzo de 2018.</p> </div> <h3 class="tituloCaja">Enlaces relacionados</h3>'
        m_download.get_response.return_value = resp
        fo = mock.MagicMock()
        m_open.return_value.__enter__.return_value = fo
        m_os.path.exists.return_value = False
        self.m_cdau.get_metadata = get_func(cdau.Reader.get_metadata)
        self.m_cdau.get_metadata(self.m_cdau, 'xxx')
        self.assertEqual(self.m_cdau.src_date, '2018-03-05')
        m_open.assert_called_once_with('xxx', 'w')
        fo.write.assert_called_once_with('2018-03-05')
        resp.text = ''
        with self.assertRaises(IOError):
            self.m_cdau.get_metadata(self.m_cdau, 'xxx')
        m_open.reset_mock()
        m_open.return_value.__enter__.return_value.read.return_value = 'foobar'
        m_os.path.exists.return_value = True
        self.m_cdau.get_metadata(self.m_cdau, 'xxx')
        self.assertEqual(self.m_cdau.src_date, 'foobar')
        m_open.assert_called_once_with('xxx', 'r')

    def test_get_cat_address(self):
        ad = {
            'dgc_via': '123', 
            'refcatparc': 'foobar',
            'nom_tip_via': 'CALLE',
            'nom_via': "Alegría",
            'cod_postal': '12345',
            'num_por_desde': '10', 'ext_desde': 'A',
            'num_por_hasta': '', 'ext_hasta': ''
        }
        attr = cdau.get_cat_address(ad, '29900')
        self.assertEqual(attr['localId'], '29.900.123.foobar')
        self.assertEqual(attr['TN_text'], "CL Alegría")
        self.assertEqual(attr['postCode'], '12345')
        self.assertEqual(attr['spec'], 'Entrance')
        self.assertEqual(attr['designator'], '10A')

        ad.update({'num_por_hasta': '14', 'ext_hasta': 'D'})
        attr = cdau.get_cat_address(ad, '29900')
        self.assertEqual(attr['designator'], '10A-14D')
