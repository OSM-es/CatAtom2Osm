import unittest

import mock

from catatom2osm.overpass import Query, api_servers


class TestQuery(unittest.TestCase):

    @mock.patch.object(Query, 'set_search_area')
    def test_init(self, m_q):
        q = Query('foo')
        self.assertEqual(q.output, 'xml')
        self.assertEqual(q.down, '(._;>>;);')
        self.assertEqual(q.meta, 'out meta;')
        self.assertEqual(q.area_id, '')
        self.assertEqual(q.bbox, '')
        self.assertEqual(q.statements, [])
        m_q.assert_called_once_with('foo')
        self.assertEqual(q.url, '')
        q = Query('foo', 'json', False, False)
        self.assertEqual(q.output, 'json')
        self.assertEqual(q.down, '')
        self.assertEqual(q.meta, 'out;')

    def test_set_search_area(self):
        q = Query('12345678')
        self.assertEqual(q.area_id, '12345678')
        q.set_search_area('1,-2, 3.1,-4.99')
        self.assertEqual(q.bbox, '1,-2, 3.1,-4.99')
        with self.assertRaises(TypeError):
            q.set_search_area('123456789')
        with self.assertRaises(TypeError):
            q.set_search_area('123x5678')
        with self.assertRaises(TypeError):
            q.set_search_area('-1')
        with self.assertRaises(TypeError):
            q.set_search_area('1, 2a, 3, 4')
        with self.assertRaises(TypeError):
            q.set_search_area('1, 2, 3')
        with self.assertRaises(TypeError):
            q.set_search_area('1; 2; 3; 4')

    def test_add(self):
        q = Query('1').add('foo;bar;')
        q.add(['taz', 'zap;']).add('raz')
        self.assertEqual(set(q.statements), {'foo', 'bar', 'taz', 'zap', 'raz'})
        q.statements = []
        q.add('1', '2', '3')
        self.assertEqual(set(q.statements), {'1', '2', '3'})

    def test_get_url(self):
        q = Query('1234')
        self.assertEqual(q.get_url(), '')
        q.add('foo', 'bar')
        url = api_servers[0] + "data=[out:xml][timeout:250];(area(3600001234)" \
            "->.searchArea;foo(area.searchArea);bar(area.searchArea););" \
            "(._;>>;);out meta;"
        self.assertEqual(q.get_url(), url)
        q = Query('1,2,3,4', 'json', False, False)
        q.add('foo', 'bar')
        url = api_servers[1] + "data=[out:json][timeout:250];(foo(1,2,3,4);" \
            "bar(1,2,3,4););out;"
        self.assertEqual(q.get_url(1), url)

    @mock.patch('catatom2osm.overpass.download')
    def test_download(self, m_download):
        def raises_io(*args):
            raise IOError()
        def raises_io1(url, fn):
            if url == api_servers[0]:
                raise IOError()
        q = Query('1,2,3,4').add('foo')
        q.download('bar')
        m_download.wget.assert_called_once_with(q.get_url(0), 'bar')
        m_download.wget = raises_io
        with self.assertRaises(IOError):
            q.download('bar')
        m_download.wget = raises_io1
        q.download('bar')

    @mock.patch('catatom2osm.overpass.download')
    def test_read(self, m_download):
        m_download.get_response.return_value.text.encode.return_value = 'bar'
        q = Query('1,2,3,4').add('foo')
        out = q.read()
        m_download.get_response.assert_called_once_with(q.get_url())
        self.assertEqual(out, 'bar')

