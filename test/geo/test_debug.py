import unittest

import mock

from catatom2osm.app import QgsSingleton
from catatom2osm.geo.debug import DebugWriter
from catatom2osm.geo.layer.base import BaseLayer
from catatom2osm.geo.layer.highway import HighwayLayer
from catatom2osm.geo.point import Point

qgs = QgsSingleton()


class TestDebugWriter(unittest.TestCase):
    def tearDown(self):
        BaseLayer.delete_shp("test")

    def test_init(self):
        layer = HighwayLayer()
        db = DebugWriter("test", layer, "memory")
        self.assertEqual(db.fields[0].name(), "note")
        self.assertEqual(db.writer.hasError(), 0)

    def test_add_point(self):
        layer = HighwayLayer()
        db = DebugWriter("test", layer, "memory")
        db.add_point(Point(0, 0), "foobar")
        db.add_point(Point(0, 0))
