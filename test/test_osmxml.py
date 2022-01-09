import unittest
from io import StringIO, BytesIO

from catatom2osm import osm, osmxml
from catatom2osm.osmxml import etree


class OsmxmlTest(unittest.TestCase):

    def test_serialize(self):
        data = osm.Osm()
        n = data.Node(4,0)
        n.tags['entrance'] = 'yes'
        n.tags['addr:street'] = "Calle la Ñ"
        n.tags['addr:housenumber'] = '7'
        w = data.Way([(12,0), (14,0), (14,2), (12,2), (12,0)])
        w.tags['leisure'] = 'swiming_pool'
        r = data.MultiPolygon([[
            [(0,0), (10,0), (10,6), (0,6), (0,0)], 
            [(8,1), (9,1), (9,2), (8,2), (8,1)]
        ]])
        r.tags['building'] = 'residential'
        fo = StringIO()
        osmxml.serialize(fo, data)
        result = bytes(fo.getvalue().encode('utf-8'))
        root = etree.fromstring(result)
        for (xmlnode, osmnode) in zip(root.findall('node'), data.nodes):
            self.assertEqual(float(xmlnode.get('lon')), osmnode.x) 
            self.assertEqual(float(xmlnode.get('lat')), osmnode.y)
        for (xmltag, osmtag) in zip(root.findall('node/tag'), n.tags.items()):
            self.assertEqual(xmltag.get('k'), osmtag[0])
            self.assertEqual(xmltag.get('v'), osmtag[1])
        nw = 0
        for (xmlway, osmway) in zip(root.findall('way'), data.ways):
            nw += 1
            for (xmlnd, osmnd) in zip(xmlway.findall('nd'), osmway.nodes):
                self.assertEqual(int(xmlnd.get('ref')), osmnd.id)
        self.assertEqual(nw, 3)
        for (xmltag, osmtag) in zip(root.findall('way/tag'), w.tags.items()):
            self.assertEqual(xmltag.get('k'), osmtag[0])
            self.assertEqual(xmltag.get('v'), osmtag[1])
        for (i, (xmlm, osmm)) in enumerate(zip(root.findall('relation/member'), r.members)):
            self.assertEqual(int(xmlm.get('ref')), osmm.ref)
            self.assertEqual(xmlm.get('role'), 'outer' if i == 0 else 'inner')
        for (xmltag, osmtag) in zip(root.findall('relation/tag'), r.tags.items()):
            self.assertEqual(xmltag.get('k'), osmtag[0])
            self.assertEqual(xmltag.get('v'), osmtag[1])
        self.assertEqual(sum([1 for r in root.findall('relation')]), 1)
        self.assertEqual(root.find('note'), None)
        self.assertEqual(root.find('meta'), None)
        data.note = 'foobar'
        data.meta = {'foo': 'bar'}
        data.tags['type'] = 'import'
        fo = StringIO()
        osmxml.serialize(fo, data)
        result = bytes(fo.getvalue().encode('utf-8'))
        root = etree.fromstring(result)
        self.assertEqual(root.find('note').text, 'foobar')
        self.assertEqual(root.find('meta').get('foo'), 'bar')
        for (xmltag, osmtag) in zip(root.findall('changeset/tag'), data.tags.items()):
            self.assertEqual(xmltag.get('k'), osmtag[0])
            self.assertEqual(xmltag.get('v'), osmtag[1])

    def test_deserialize(self):
        attrs = dict(upload='1', version='2', generator='3')
        root = etree.Element('osm', attrs)
        nodexml = etree.Element('node', dict(id='-1', lon='4', lat='0'))
        nodexml.append(etree.Element('tag', dict(k='entrance', v='yes')))
        nodexml.append(etree.Element('tag', dict(k='addr:street', v="Calle la Ñ")))
        nodexml.append(etree.Element('tag', dict(k='addr:housenumber', v='7')))
        root.append(nodexml)
        wayxml = etree.Element('way', dict(id='-100'))
        for (i, node) in enumerate([(12,0), (14,0), (14,2), (12,2), (12,0)]):
            nodexml = etree.Element('node', dict(id=str(-i-10), lon=str(node[0]), lat=str(node[1])))
            root.append(nodexml)
            wayxml.append(etree.Element('nd', dict(ref=str(nodexml.get('id')))))
        wayxml.append(etree.Element('tag', dict(k='leisure', v='swiming_pool')))
        root.append(wayxml)
        wayxml = etree.Element('way', dict(id='-101'))
        for (i, node) in enumerate([(0,0), (10,0), (10,6), (0,6), (0,0)]):
            nodexml = etree.Element('node', dict(id=str(-i-20), lon=str(node[0]), lat=str(node[1])))
            root.append(nodexml)
            wayxml.append(etree.Element('nd', dict(ref=str(nodexml.get('id')))))
        root.append(wayxml)
        wayxml = etree.Element('way', dict(id='-102'))
        for (i, node) in enumerate([(8,1), (9,1), (9,2), (8,2), (8,1)]):
            nodexml = etree.Element('node', dict(id=str(-i-30), lon=str(node[0]), lat=str(node[1])))
            root.append(nodexml)
            wayxml.append(etree.Element('nd', dict(ref=str(nodexml.get('id')))))
        root.append(wayxml)
        relxml = etree.Element('relation', dict(id='-200'))
        relxml.append(etree.Element('member', dict(type='way', ref='-101', role='outter')))
        relxml.append(etree.Element('member', dict(type='way', ref='-102', role='inner')))
        relxml.append(etree.Element('member', dict(type='relation', ref='-201')))
        relxml.append(etree.Element('tag', dict(k='building', v='residential')))
        root.append(relxml)
        relxml = etree.Element('relation', dict(id='-201'))
        relxml.append(etree.Element('tag', dict(k='test', v='nested relation')))
        relxml.append(etree.Element('member', dict(type='way', ref='-101', role='dummy')))
        root.append(relxml)
        root.append(etree.Element('dummy'))
        fo = BytesIO(etree.tostring(root))
        result = osmxml.deserialize(fo)
        self.assertEqual(result.upload, '1')
        self.assertEqual(result.version, '2')
        self.assertEqual(result.generator, '3')
        self.assertEqual(len(result.nodes), 16)
        for osmnode in result.nodes:
            xmlnode = root.find("node[@id='%d']" % osmnode.id)
            self.assertEqual(float(xmlnode.get('lon')), osmnode.x) 
            self.assertEqual(float(xmlnode.get('lat')), osmnode.y)
        n = result.get('-1')
        self.assertEqual(n.tags['entrance'], 'yes')
        self.assertEqual(n.tags['addr:street'], "Calle la Ñ")
        self.assertEqual(n.tags['addr:housenumber'], '7')
        self.assertEqual(len(result.ways), 3)
        for osmway in result.ways:
            xmlway = root.find("way[@id='%d']" % osmway.id)
            for nd in xmlway.findall('nd'):
                self.assertIn(nd.get('ref'), [str(w.id) for w in osmway.nodes])
        w = result.get('-100', 'w')
        self.assertEqual(w.tags['leisure'], 'swiming_pool')
        self.assertEqual(len(result.relations), 2)
        osmrel = result.get(-200, 'r')
        xmlrel = root.find("relation[@id='%d']" % osmrel.id)
        roles = []
        for m in xmlrel.findall('member'):
            self.assertIn(m.get('ref'), [str(x.ref) for x in osmrel.members])
            roles.append(m.get('role'))
        self.assertEqual(roles, ['outter', 'inner', None])
        r = result.get(-200, 'r')
        self.assertEqual(r.tags['building'], 'residential')
        nxml = etree.Element('note')
        nxml.text = 'foobar'
        root.append(nxml)
        mxml = etree.Element('meta')
        mxml.set('foo', 'bar')
        root.append(mxml)
        csxml = etree.Element('changeset')
        csxml.append(etree.Element('tag', dict(k='type', v='import')))
        root.append(csxml)
        fo = BytesIO(etree.tostring(root))
        result = osmxml.deserialize(fo)
        self.assertEqual(result.tags, dict(type='import'))
        self.assertEqual(result.note, 'foobar')
        self.assertEqual(result.meta, dict(foo='bar'))
        root = etree.Element('osm')
        nodexml = etree.Element('node', dict(id='-50', lon='0', lat='4'))
        root.append(nodexml)
        fo = BytesIO(etree.tostring(root))
        result = osmxml.deserialize(fo, result)
        self.assertEqual(len(result.nodes), 17)
        root = etree.Element('osm')
        wayxml = etree.Element('way', dict(id='-103', version='1'))
        wayxml.append(etree.Element('nd', dict(ref='-99')))
        root.append(wayxml)
        relxml = etree.Element('relation', dict(id='-202'))
        relxml.append(etree.Element('member', dict(type='way', ref='-199', role='dummy')))
        root.append(relxml)
        fo = BytesIO(etree.tostring(root))
        result = osmxml.deserialize(fo, result)
        self.assertEqual(len(result.nodes), 17)
        self.assertEqual(len(result.ways), 4)
        self.assertEqual(len(result.relations), 3)
        self.assertEqual(result.get(-103, 'w').version, '2')
        self.assertEqual(result.get(-202, 'r').version, None)
