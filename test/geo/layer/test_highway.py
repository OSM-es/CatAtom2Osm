import unittest

import mock

from catatom2osm import osm
from catatom2osm.app import QgsSingleton
from catatom2osm.geo.layer.highway import HighwayLayer
from catatom2osm.geo.point import Point

qgs = QgsSingleton()


class TestHighwayLayer(unittest.TestCase):
    def test_init(self):
        layer = HighwayLayer()
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.fields()[0].name(), "name")
        self.assertEqual(layer.crs().authid(), "EPSG:4326")

    def test_read_from_osm(self):
        layer = HighwayLayer()
        data = osm.Osm()
        w1 = data.Way(((10, 10), (15, 15)), {"name": "FooBar"})
        w2 = data.Way(((20, 20), (30, 30)))
        r = data.Relation([w2], {"name": "BarTaz"})
        layer.read_from_osm(data)
        self.assertEqual(layer.featureCount(), 2)
        names = [feat["name"] for feat in layer.getFeatures()]
        self.assertIn("BarTaz", names)
        self.assertIn("FooBar", names)
        for f in layer.getFeatures():
            if f["name"] == "FooBar":
                self.assertEqual(
                    f.geometry().asPolyline(), [Point(10, 10), Point(15, 15)]
                )
            if f["name"] == "BarTaz":
                self.assertEqual(
                    f.geometry().asPolyline(), [Point(20, 20), Point(30, 30)]
                )
