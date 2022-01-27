import unittest

from qgis.core import QgsFeature, QgsFields

from catatom2osm.geo import Geometry, Point


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
