import unittest
import random
from collections import Counter

from catatom2osm import osm

class OsmTestCase(unittest.TestCase):

    def setUp(self):
        self.d = osm.Osm()


class TestOsm(OsmTestCase):

    def test_init(self):
        self.assertEqual(self.d.counter, 0)
        self.assertEqual(self.d.elements, set())

    def test_getattr(self):
        n = self.d.Node(1,1)
        self.assertEqual((n.x, n.y), (1,1))
        with self.assertRaises(AttributeError):
            self.d.node
        
    def test_properties(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(0,0)
        w = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        r = self.d.Relation([n1, w])
        self.assertEqual(len(self.d.nodes), 6)
        self.assertEqual(self.d.ways, [w])
        self.assertEqual(self.d.relations, [r])

    def test_remove(self):
        n0 = self.d.Node(0,0)
        n1 = self.d.Node(1,0)
        n2 = self.d.Node(1,1)
        n3 = self.d.Node(0,1)
        n4 = self.d.Node(2,0)
        n5 = self.d.Node(2,1)
        n6 = self.d.Node(1,0.5)
        w1 = self.d.Way((n1, n0, n3, n2))
        w2 = self.d.Way((n1, n6, n2))
        w3 = self.d.Way((n1, n4, n5, n2))
        r1 = self.d.Relation((w1, w2))
        r2 = self.d.Relation((w2, w3))
        self.assertEqual(len(self.d.elements), 12)
        self.assertIn(w2, self.d.parents[n6])
        self.d.remove(w2)
        self.assertEqual(len(self.d.elements), 10)
        self.assertNotIn(w2, self.d.elements)
        self.assertNotIn(n6, self.d.elements)
        self.d.remove(n2)
        self.assertEqual(len(self.d.elements), 9)
        self.assertNotIn(n2, self.d.elements)
        self.d.remove(r2)
        self.assertEqual(len(self.d.elements), 5)
        self.assertNotIn(w3, self.d.elements)
        self.assertNotIn(r2, self.d.elements)
        self.assertNotIn(n4, self.d.elements)
        self.assertNotIn(n5, self.d.elements)
        self.d.remove(r1)
        self.assertEqual(len(self.d.parents[n1]), 0)
        self.assertEqual(len(self.d.elements), 0)

    def test_replace(self):
        n1 = self.d.Node(1,1)
        d2 = osm.Osm()
        n2 = d2.Node(2,2)
        p = self.d.parents[n1]
        self.d.replace(n1, n2)
        self.assertNotIn(n1, self.d.elements)
        self.assertIn(n2, self.d.elements)
        self.assertEqual(n2.container, self.d)
        self.assertEqual(self.d.get(n2.id), n2)
        self.assertEqual(self.d.parents[n2], p)

    def test_merge_duplicated(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(2,2)
        n3 = self.d.Node(3,3, {'a': 'b'})
        n3id = n3.id
        n4 = self.d.Node(4,4)
        n4.id = 1
        n5 = self.d.Node(4,4)
        n6 = self.d.Node(4,4)
        n6.id = 2
        n7 = self.d.Node(3,3)
        n8 = self.d.Node(5,5, {'a': '1'})
        n9 = self.d.Node(5,5, {'b': '2'})
        n10 = self.d.Node(5,5)
        w1 = self.d.Way([(1,1), (1,0), (2,2), (3,2), (3,3)])
        w1id = w1.id
        r1 = self.d.Relation([w1, n3])
        w2 = self.d.Way([(1,1), (1,0), (2,2), (3,2), (3,3)], {'x': 'y'})
        w2id = w2.id
        r2 = self.d.Relation([w2])
        self.assertFalse(w1.nodes[0] is n1)
        self.assertFalse(w1.nodes[2] is n2)
        self.assertNotEqual(r1.members[0].ref, r2.members[0].ref)
        self.d.merge_duplicated()
        duped = Counter()
        for n in self.d.nodes:
            duped[(n.x, n.y)] += 1
        for position, count in list(duped.items()):
            if position in ((4,4), (5,5)):
                self.assertEqual(count, 2)
            else:
                self.assertEqual(count, 1)
        self.assertIn(w1.nodes[0], self.d.elements)
        self.assertIn(w1.nodes[2], self.d.elements)
        self.assertEqual(w1.nodes[4].id, n3id)
        self.assertEqual(w1.nodes[4].tags['a'], 'b')
        self.assertIn(n8, self.d.elements)
        self.assertIn(n9, self.d.elements)
        self.assertEqual(r1.members[0].ref, w2id)
        self.assertEqual(r2.members[0].ref, w2id)
        self.assertEqual(r1.members[0].element.tags['x'], 'y')
        self.assertEqual(r2.members[0].element.tags['x'], 'y')
        self.assertNotIn(w1id, self.d.index)

    def test_attrs(self):
        self.assertEqual(self.d.attrs, dict(upload='never', version='0.6'))
        self.d.generator = 'yo'
        self.assertEqual(self.d.attrs['generator'], 'yo')
        self.d.upload = 'yes'
        self.assertNotIn('upload', list(self.d.attrs.keys()))

    def test_index(self):
        n = self.d.Node(1,1)
        w = self.d.Way([n])
        r = self.d.Relation([w,n])
        self.assertEqual(self.d.index['n-1'], n)
        self.assertEqual(self.d.index['w-2'], w)
        self.assertEqual(self.d.index['r-3'], r)

    def test_get(self):
        n = self.d.Node(1,1)
        w = self.d.Way([n])
        r = self.d.Relation([w,n])
        self.assertEqual(self.d.get(-1), n)
        self.assertEqual(self.d.get('-1'), n)
        self.assertEqual(self.d.get('w-2'), w)
        self.assertEqual(self.d.get('-3', 'Relation'), r)


class TestOsmElement(OsmTestCase):

    def test_init(self):
        e1 = osm.Element(self.d, {'foo': 'bar'})
        e2 = osm.Element(self.d)
        self.assertEqual(e1.container, self.d)
        self.assertEqual(e1.tags['foo'], 'bar')
        self.assertEqual(e1.id, -1)
        self.assertEqual(e2.id, -2)
        e3 = osm.Element(self.d, attrs={'id': '4'})
        self.assertEqual(e3.id, 4)
        self.assertEqual(self.d.counter, -2)

    def test_is_new(self):
        e = osm.Element(self.d)
        self.assertTrue(e.is_new())
        e.id = -random.randint(0,1000)
        self.assertTrue(e.is_new())
        e.id = random.randint(0,1000)
        self.assertFalse(e.is_new())

    def test_attrs(self):
        e = osm.Element(self.d)
        self.assertEqual(e.attrs, dict(action=e.action, visible=e.visible, id='-1'))
        e.id = 1
        self.assertEqual(e.attrs['id'], '1')
        e.version = '2'
        self.assertEqual(e.attrs['version'], '2')
        e.timestamp = '3'
        self.assertEqual(e.attrs['timestamp'], '3')
        e.changeset = '4'
        self.assertEqual(e.attrs['changeset'], '4')
        e.uid = '5'
        self.assertEqual(e.attrs['uid'], '5')
        e.user = '6'
        self.assertEqual(e.attrs['user'], '6')
        
    def test_set_attrs(self):
        e = osm.Element(self.d)
        e.attrs = dict(id=1, action='Delete', visible='False', foo='bar')
        self.assertEqual(e.id, 1)
        self.assertEqual(e.action, 'Delete')
        self.assertFalse(hasattr(e, 'foo'))


class TestOsmNode(OsmTestCase):

    def test_init(self):
        n1 = self.d.Node(1, 2, {'foo': 'bar'})
        self.assertEqual(n1.tags['foo'], 'bar')
        self.assertEqual((n1.x, n1.y), (1, 2))
        self.assertEqual(n1.fid, 'n%d' % n1.id)
        self.assertEqual(n1.type, 'node')
        n2 = self.d.Node((2,3), tags={'a': 'b'})
        self.assertEqual(n2.tags['a'], 'b')
        self.assertEqual((n2.x, n2.y), (2, 3))
        
    def test_init_round(self):
        osm.COOR_DIGITS = 2
        n = self.d.Node(1.001, 2.0055)
        self.assertEqual(n.x, 1.00)
        self.assertEqual(n.y, 2.01)
        osm.COOR_DIGITS = 0
        n = self.d.Node(1.001, 2.0055)
        self.assertEqual(n.x, 1.001)
        self.assertEqual(n.y, 2.0055)

    def test_eq(self):
        n1 = self.d.Node(1, 2)
        self.assertEqual(n1, (1, 2))
        n2 = self.d.Node(1, 2)
        self.assertEqual(n1, n2)
        self.assertEqual(n2, n1)
        n1.tags['a'] = '1'
        n2.tags['a'] = '1'
        self.assertEqual(n1, n2)
        n1.tags = {}
        n2.id = 2
        self.assertEqual(n1, n2)
        
    def test_ne(self):
        n1 = self.d.Node(1, 2, {'c': 'd'})
        n2 = self.d.Node(1, 2, {'a': 'b'})
        self.assertNotEqual(n1, n2)
        self.assertNotEqual(n2, n1)
        n1.tags['a'] = 'b'
        n1.id = 1
        self.assertNotEqual(n1, n2)
        n1.tags = {}
        self.assertNotEqual(n1, (1, 2))
        
    def test_getitem(self):
        n = self.d.Node(1, 2)
        self.assertEqual(n[0], 1)
        self.assertEqual(n[1], 2)
        with self.assertRaises(IndexError):
            n[2]

    def test_childs(self):
        n = self.d.Node(3,3)
        self.assertEqual(len(n.childs), 0)

    def test_latlon(self):
        n = self.d.Node(1,2)
        self.assertEqual(n.lon, '1')
        self.assertEqual(n.lat, '2')
        n.lon = 2
        n.lat = 1
        self.assertEqual(n.lon, '2.0')
        self.assertEqual(n.lat, '1.0')

    def test_geometry(self):
        n = self.d.Node(1,2)
        self.assertEqual(n.geometry(), (1,2))
        
    def test_attrs(self):
        n = self.d.Node(1, 2)
        n.id = 3
        self.assertEqual(n.attrs['lon'], '1')
        self.assertEqual(n.attrs['lat'], '2')
        self.assertEqual(n.attrs['id'], '3')

    def test_set_attrs(self):
        n = self.d.Node(0, 0)
        n.attrs = dict(id='1', lon='2', lat='3')
        self.assertEqual(n.id, 1)
        self.assertEqual(n.x, 2)
        self.assertEqual(n.y, 3)

    def test_str(self):
        n = self.d.Node(1, 2)
        self.assertEqual(str(n), str((n.x, n.y)))


class TestOsmWay(OsmTestCase):

    def test_init(self):
        n1 = self.d.Node(1,2)
        n2 = self.d.Node(2,3)
        n3 = self.d.Node(3,4)
        w = self.d.Way([(1,2), n2, (3,4)])
        self.assertEqual(w.nodes, [n1, n2, n3])
        self.assertEqual(w.fid, 'w%d' % w.id)
        self.assertEqual(w.type, 'way')

    def test_childs(self):
        n = self.d.Node(3,3)
        w = self.d.Way(((1,1), (2,2), n, (4,4), n, (5,5)))
        self.assertEqual(len(w.childs), 5)
        for n in w.nodes:
            self.assertIn(n, w.childs)

    def test_append(self):
        w = self.d.Way()
        self.assertEqual(w.nodes, [])
        n1 = self.d.Node(1,1)
        w.append((1,1))
        self.assertEqual(w.nodes, [n1])
        n2 = self.d.Node(2,2)
        w.append(n2)
        self.assertEqual(w.nodes, [(1,1), (2,2)])

    def test_remove(self):
        n = self.d.Node(3,3)
        w = self.d.Way(((1,1), (2,2), n, (4,4), n, (5,5)))
        self.assertEqual(len(w.nodes), 6)
        w.remove(n)
        self.assertEqual(len(w.nodes), 4)
        self.assertNotIn(n, w.nodes)
        self.assertNotIn(w, self.d.parents[n])

    def test_replace(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,2)   
        n3 = self.d.Node(2,3)
        n4 = self.d.Node(3,4)
        w = self.d.Way([n1, n2, n4])
        w.replace(n2, n3)
        self.assertEqual(w.nodes, [n1, n3, n4])
        #self.assertNotIn(w, self.d.parents[n1])
        #self.assertIn(w, self.d.parents[n2])
        
    def test_eq(self):
        n = self.d.Node(1,1)
        w1 = self.d.Way([n, (2,2), (3,3)])
        w2 = self.d.Way([(1,1), (2,2), (3,3)])
        self.assertEqual(w1, w2)
        n.tags['foo'] = 'bar'
        self.assertEqual(w1, w2)
        g = tuple((x, x) for x in range(7)) + ((0,0),)
        w1 = self.d.Way(g, dict(foo='bar'))
        w2 = self.d.Way(g[3:] + g[1:4])
        self.assertEqual(w1, w2)
        g = g[3:] + g[1:4]
        self.assertNotEqual(w1, g)
        w1.tags = {}
        self.assertEqual(w1, g)
        self.assertEqual(w2, g)

    def test_ne(self):
        n = self.d.Node(1,1)
        w1 = self.d.Way([n, (2,2), (3,3)])
        w2 = self.d.Way([(2,2), (3,3), (1,1)])
        self.assertNotEqual(w1, w2)
        g1 = tuple((x, x) for x in range(7)) + ((0,0),)
        g2 = tuple((x, x) for x in range(8)) + ((0,0),)
        w1 = self.d.Way(g1)
        self.assertNotEqual(w1, g2)

    def test_is_open(self):
        w = self.d.Way(((1,1), (2,2)))
        self.assertTrue(w.is_open())
        self.assertFalse(w.is_closed())
        w.append(self.d.Node(1,2))
        w.append(self.d.Node(1,1))
        self.assertFalse(w.is_open())
        self.assertTrue(w.is_closed())

    def test_shoelace(self):
        w1 = self.d.Way([(0,0), (1,0), (1,1), (0,1), (0,0)])
        w2 = self.d.Way([(0,0), (0,1), (1,1), (1,0), (0,0)])
        self.assertGreater(w1.shoelace(), 0)
        self.assertLess(w2.shoelace(), 0)
        w3 = self.d.Way()
        self.assertEqual(w3.shoelace(), 0)

    def test_geometry(self):
        g = ((0,0), (6,0), (5,1), (4,2), (3,3), (2,4), (1,5), (0,0))
        w1 = self.d.Way(g)
        w2 = self.d.Way(g[3:] + g[1:4])
        w3 = self.d.Way(g[:4])
        w4 = self.d.Way(g[::-1])
        self.assertEqual(w1.geometry(), g)
        self.assertEqual(w2.geometry(), g)
        self.assertEqual(w3.geometry(), g[:4])
        self.assertEqual(w4.geometry(), w1.geometry())
        
    def test_clean_duplicated_nodes(self):
        w = self.d.Way([(0,0), (1,1), (1,1), (2,2)])
        w.clean_duplicated_nodes()
        self.assertEqual(len(w.nodes), 3)
        w = self.d.Way()
        w.clean_duplicated_nodes()
        self.assertEqual(len(w.nodes), 0)
 
    def test_search_node(self):
        n = self.d.Node(1,1)
        w = self.d.Way([(0,0), n, (2,2)])
        self.assertTrue(w.search_node(1, 1) is n)
        self.assertEqual(w.search_node(5, 0), None)
        

class TestOsmRelation(OsmTestCase):

    def test_init(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(0,0)
        w = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        r = self.d.Relation([n1, w, osm.Relation.Member(n2)])
        self.assertEqual(r.members[0].element, n1)
        self.assertEqual(r.members[1].element, w)
        self.assertEqual(r.members[2].element, n2)
        self.assertEqual(r.container, self.d)
        self.assertEqual(r.fid, 'r%d' % r.id)
        self.assertEqual(r.type, 'relation')

    def test_append(self):
        n1 = self.d.Node(1,1)
        r = self.d.Relation()
        r.append(n1, 'foobar')
        self.assertEqual(r.members[0].element, n1)
        self.assertEqual(r.members[0].role, 'foobar')
        self.assertIn(r, self.d.parents[n1])
    
    def test_member_eq(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,1)
        m1 = osm.Relation.Member(n1, 'foo')
        m2 = osm.Relation.Member(n1, 'foo')
        self.assertEqual(m1, m2)

    def test_member_ne(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,1)
        m1 = osm.Relation.Member(n1, 'foo')
        m2 = osm.Relation.Member(n1, 'bar')
        m3 = osm.Relation.Member((1,1), 'foo')
        self.assertNotEqual(m1, m2)
        n1.id = 1
        self.assertNotEqual(m1, m3)
        self.assertNotEqual(m1, 'foobar')

    def test_eq(self):
        n = self.d.Node(1,1)
        w = self.d.Way([n, (2,2), (3,3)])
        r1 = self.d.Relation([n, w])
        r2 = self.d.Relation([n, w])
        self.assertEqual(r1, r2)
        
    def test_ne(self):
        n = self.d.Node(1,1)
        w = self.d.Way([n, (2,2), (3,3)])
        r1 = self.d.Relation([n, w])
        r2 = self.d.Relation([n, w])
        r2.append(n, 'foo')
        r2.append(w, 'bar')
        r3 = self.d.Relation([(1,1), w])
        self.assertNotEqual(r1, r2)
        n.id = 1
        self.assertNotEqual(r1, r3)

    def test_geometry(self):
        g1 = ((1,1), (2,2), (3,3))
        w1 = self.d.Way(g1)
        g2 = ((0,0), (1,2), (2,3))
        w2 = self.d.Way(g2)
        n = self.d.Node(4,4)
        r = self.d.Relation([w1, w2, n])
        self.assertEqual(r.geometry(), (g1, g2, (4,4)))

    def test_childs(self):
        n = self.d.Node(3,3)
        r = self.d.Relation()
        for i in range(1,7):
            if i in (3,5):
                r.append(n)
            else:
                r.append(self.d.Node(i, i))
        self.assertEqual(len(r.childs), 5)
        for m in r.members:
            self.assertIn(m.element, r.childs)

    def test_remove(self):
        n = self.d.Node(3,3)
        r = self.d.Relation()
        for i in range(1,7):
            if i in (3,5):
                r.append(n)
            else:
                r.append(self.d.Node(i, i))
        self.assertEqual(len(r.members), 6)
        r.remove(n)
        self.assertEqual(len(r.members), 4)
        self.assertNotIn(n, r.childs)
        self.assertNotIn(r, self.d.parents[n])

    def test_replace(self):
        n1 = self.d.Node(1,1)
        n2 = self.d.Node(1,2)
        n3 = self.d.Node(2,3)
        n4 = self.d.Node(3,4)
        r = self.d.Relation([n1, n2, n4])
        r.replace(n2, n3)
        self.assertEqual([m.element for m in r.members], [n1, n3, n4])
        self.assertNotIn(r, self.d.parents[n2])
        self.assertIn(r, self.d.parents[n3])

    def test_type(self):
        n = self.d.Node(1,1)
        w = self.d.Way(((1,1), (2,2), (3,3)))
        r = self.d.Relation([n, w])
        m = osm.Relation.Member(n)
        self.assertEqual(m.type, 'node')
        m = osm.Relation.Member(w)
        self.assertEqual(m.type, 'way')
        m = osm.Relation.Member(r)
        self.assertEqual(m.type, 'relation')
    
    def test_ref(self):
        n = self.d.Node(1,1)
        m = osm.Relation.Member(n)
        self.assertEqual(m.ref, n.id)
        n.id = 100
        self.assertEqual(m.ref, 100)

    def test_member_attrs(self):
        n = self.d.Node(1,1)
        n.id = -1
        m = osm.Relation.Member(n)
        self.assertEqual(m.attrs, dict(type='node', ref=str(n.id)))
        m.role = 'outter'
        self.assertEqual(m.attrs['role'], m.role)
    
    def test_is_valid_multipolygon(self):
        n0 = self.d.Node(0,0)
        r0 = self.d.Relation([n0])
        self.assertFalse(r0.is_valid_multipolygon())
        w0 = self.d.Way([(0,0)])
        r1 = self.d.Relation()
        r1.append(w0, 'outer')
        self.assertFalse(r1.is_valid_multipolygon())
        w0.nodes += [self.d.Node(5,0), self.d.Node(5,5), self.d.Node(0,0)]
        self.assertTrue(r1.is_valid_multipolygon())
        r1.members[0].role = 'foobar'
        self.assertFalse(r1.is_valid_multipolygon())
        r1.members[0].role = 'outer'
        self.assertTrue(r1.is_valid_multipolygon())
        w1 = self.d.Way(((1,1), (2,1), (2,2)))
        w2 = self.d.Way(((1,1), (2,2)))
        r1.append(w1, 'inner')
        self.assertFalse(r1.is_valid_multipolygon())
        r1.append(w2, 'inner')
        self.assertTrue(r1.is_valid_multipolygon())
        r1.append(r0)
        self.assertFalse(r1.is_valid_multipolygon())

    def test_outer_geometry(self):
        r = self.d.Relation()
        w0 = ((0,0), (1,0), (1,1), (0,0))
        r.append(self.d.Way(w0), 'outer')
        self.assertEqual(r.outer_geometry(), [w0])
        w1 = ((2,0), (4,0), (4,4), (2,4), (2,0))
        r.append(self.d.Way(w1[:3]), 'outer')
        r.append(self.d.Way(w1[2:]), 'outer')
        self.assertEqual(r.outer_geometry(), [w0, w1])
        w2 = ((2,10), (4,10), (4,14), (2,14), (2,10))
        r.append(self.d.Way(w2[:3]), 'outer')
        r.append(self.d.Way(w2[:1:-1]), 'outer')
        self.assertEqual(r.outer_geometry(), [w0, w1, w2])
        w3 = ((4, 24), (4, 20), (2, 20), (2, 24), (4, 24))
        r.append(self.d.Way(w3[:2]), 'outer')
        r.append(self.d.Way(w3[:2:-1]), 'outer')
        self.assertEqual(r.outer_geometry(), [])
        w4 = ((0,30), (1,30), (1,31), (0,30))
        r.append(self.d.Way(w4), 'outer')
        r.append(self.d.Way(w3[2:4]), 'outer')
        r.append(self.d.Way(w3[1:3]), 'outer')
        self.assertEqual(r.outer_geometry(), [w0, w1, w2, w3, w4])


class TestOsmPolygon(OsmTestCase):

    def test_init(self):
        w1 = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        w2 = self.d.Way([(0,0), (1,1), (2,2)])
        p = self.d.Polygon([w1.nodes, w2])
        self.assertEqual(p.members[0].element.nodes, w1.nodes)
        self.assertEqual(p.members[0].role, 'outer')
        self.assertEqual(p.members[1].element, w2)
        self.assertEqual(p.members[1].role, 'inner')


class TestOsmMultiPolygon(OsmTestCase):

    def test_init(self):
        w1 = self.d.Way([(1,2), (2,3), (3,2), (1,2)])
        w2 = self.d.Way([(0,0), (1,1), (2,2)])
        w3 = self.d.Way([(11,12), (12,13), (13,12), (11,12)])
        w4 = self.d.Way([(10,10), (11,11), (12,12)])
        p = self.d.MultiPolygon([[w1.nodes, w2], [w3, w4]])
        self.assertEqual(p.members[0].element.nodes, w1.nodes)
        self.assertEqual(p.members[0].role, 'outer')
        self.assertEqual(p.members[1].element, w2)
        self.assertEqual(p.members[1].role, 'inner')
        self.assertEqual(p.members[2].element, w3)
        self.assertEqual(p.members[2].role, 'outer')
        self.assertEqual(p.members[3].element, w4)
        self.assertEqual(p.members[3].role, 'inner')
