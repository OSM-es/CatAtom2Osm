import random
import unittest

from qgis.core import QgsGeometry

from catatom2osm.geo import Point


class TestPoint(unittest.TestCase):
    def test_init(self):
        p = Point(1, 2)
        q = Point(p)
        r = Point((1, 2))
        self.assertEqual(q.x(), r.x())
        self.assertEqual(q.y(), r.y())

    def test_boundigBox(self):
        radius = random.uniform(0, 100)
        point = Point(random.uniform(0, 100), random.uniform(0, 100))
        r = point.boundingBox(radius)
        self.assertEqual(round(r.center().x() * 100), round(point.x() * 100))
        self.assertEqual(round(r.center().y() * 100), round(point.y() * 100))
        self.assertEqual(round(r.width() * 100), round(radius * 200))
        self.assertEqual(round(r.height() * 100), round(radius * 200))

    def test_get_corner_context(self):
        square = QgsGeometry.fromPolygonXY(
            [
                [
                    Point(0, 0),
                    Point(50, 0.6),  # dist > 0.5, angle < 5
                    Point(100, 0),
                    Point(105, 50),  # dist > 0.5, angle > 5
                    Point(100, 100),
                    Point(2, 100.3),  # dist < 0.5, angle > 5
                    Point(0, 100),
                    Point(0.3, 50),  # dist < 0.5, angle < 5
                    Point(0, 1),
                    Point(-50, 0),  # acute
                    Point(0, 0),
                ]
            ]
        )
        acute_thr = 10
        straight_thr = 5
        cath_thr = 0.5
        (a, is_acute, is_corner, c) = Point(50, 0.4).get_corner_context(
            square, acute_thr, straight_thr, cath_thr
        )
        self.assertFalse(is_acute)
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(105, 51).get_corner_context(
            square, acute_thr, straight_thr, cath_thr
        )
        self.assertTrue(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(5.1, 100).get_corner_context(
            square, acute_thr, straight_thr, cath_thr
        )
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(0.4, 50).get_corner_context(
            square, acute_thr, straight_thr, cath_thr
        )
        self.assertFalse(is_corner, "%f %s %s %f" % (a, is_acute, is_corner, c))
        (a, is_acute, is_corner, c) = Point(-51, 0).get_corner_context(
            square, acute_thr, straight_thr, cath_thr
        )
        self.assertTrue(is_acute)

    def test_get_spike_context(self):
        square = QgsGeometry.fromPolygonXY(
            [
                [
                    Point(0, 50),  # spike angle_v < 5 angle_a > 5 c < 0.5
                    Point(50, 50.4),
                    Point(49.9, 76),
                    Point(50, 74),  # zig-zag
                    Point(50, 130),
                    Point(50.4, 100),
                    Point(75, 110),  # spike
                    Point(99, 100),
                    Point(100, 130),  # spike but c > 0.5
                    Point(100.2, 60),
                    Point(100, 90),  # zig-zag but c > 0.1
                    Point(99.8, 0),  # spike
                    Point(99.5, 50),
                    Point(70, 55),
                    Point(60, 50),  # not zig-zag
                    Point(0, 50),
                ]
            ]
        )
        acute_thr = 5
        straight_thr = 5
        threshold = 0.5
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            50, 50.4
        ).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertFalse(is_spike)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            0, 50.1
        ).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_spike)
        self.assertEqual(ndxa, 1)
        self.assertEqual(round(vx.x(), 4), 50.0016)
        self.assertEqual(vx.y(), 50.0)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            50, 74
        ).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_zigzag)
        self.assertEqual(ndx, 3)
        self.assertEqual(ndxa, 2)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            50, 130
        ).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_spike)
        self.assertEqual(ndx, 4)
        self.assertEqual(ndxa, 5)
        self.assertEqual(vx.x(), 50)
        self.assertEqual(round(vx.y(), 4), 99.8374)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            100, 130
        ).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_acute)
        self.assertFalse(is_spike)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            100, 90
        ).get_spike_context(square, acute_thr, straight_thr, 0.1)
        self.assertFalse(is_spike)
        self.assertFalse(is_zigzag)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            100, 0
        ).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertTrue(is_spike)
        self.assertEqual(ndx, 11)
        self.assertEqual(ndxa, 12)
        self.assertEqual(round(vx.x(), 4), 99.9109)
        self.assertEqual(round(vx.y(), 4), 49.9234)
        angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx = Point(
            60, 50
        ).get_spike_context(square, acute_thr, straight_thr, threshold)
        self.assertFalse(is_zigzag)
