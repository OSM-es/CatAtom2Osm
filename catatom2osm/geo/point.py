import math

from qgis.core import QgsPoint, QgsPointXY, QgsRectangle

from catatom2osm import config


class Point(QgsPointXY):
    """Extends QgsPoint with some utility methods"""

    def __init__(self, arg1, arg2=None):
        if type(arg1) is QgsPoint:
            super(Point, self).__init__(arg1)
        elif arg2 is None:
            super(Point, self).__init__(arg1[0], arg1[1])
        else:
            super(Point, self).__init__(arg1, arg2)

    def boundingBox(self, radius):
        """Returns a bounding box of 2*radius centered in point."""
        return QgsRectangle(self.x() - radius, self.y() - radius,
                        self.x() + radius, self.y() + radius)

    def get_angle(self, geom):
        """
        For the vertex in a geometry nearest to this point, give the angle
        between its adjacent vertexs.

        Args:
            geom (QgsGeometry): Geometry to test.

        Returns:
            (float) Angle between the vertex and their adjacents,
        """
        (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(Point(self))
        va = Point(geom.vertexAt(ndxa)) # previous vertex
        vb = Point(geom.vertexAt(ndxb)) # next vertex
        angle = abs(point.azimuth(va) - point.azimuth(vb))
        return angle

    def get_corner_context(self, geom, acute_thr=config.acute_thr,
            straight_thr=config.straight_thr, cath_thr=config.dist_thr):
        """
        For the vertex in a geometry nearest to this point, give context to
        determine if it is a corner (the angle differs by more than straight_thr
        of 180 and if the distance from the vertex to the segment formed by
        their adjacents is greater than cath_thr).

        Args:
            geom (QgsGeometry): Geometry to test.
            acute_thr (float): Acute angle threshold.
            straight_thr (float): Straight angle threshold.
            cath_thr (float): Cathetus threshold.

        Returns:
            (float) Angle between the vertex and their adjacents.
            (bool)  True if the angle is too low (< acute_thr).
            (bool)  True for a corner
            (float) Distance to the nearest segment.
        """
        (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(Point(self))
        va = Point(geom.vertexAt(ndxa)) # previous vertex
        vb = Point(geom.vertexAt(ndxb)) # next vertex
        angle = abs(point.azimuth(va) - point.azimuth(vb))
        a = abs(va.azimuth(point) - va.azimuth(vb))
        h = math.sqrt(va.sqrDist(point))
        c = abs(h * math.sin(math.radians(a)))
        is_corner = abs(180 - angle) > straight_thr and c > cath_thr
        is_acute = angle < acute_thr if angle < 180 else 360 - angle < acute_thr
        return (angle, is_acute, is_corner, c)

    def get_spike_context(self, geom, acute_thr=config.acute_inv,
                          straight_thr=config.straight_thr, threshold=config.dist_inv):
        """
        For the vertex in a geometry nearest to this point, give context to
        determine if its a zig-zag or a spike. It's a zig-zag if both the angles
        of this vertex and the closest adjacents are acute. It's a spike if the
        angle of this vertex is acute and the angle of the closest vertex is
        not straight.

        Args:
            geom (QgsGeometry): Geometry to test.
            acute_thr (float): Acute angle threshold.
            straight_thr (float): Straight angle threshold.
            threshold (float): # Filter for angles.

        Returns:
            (float) angle_v = angle between the vertex and their adjacents.
            (float) angle_a = angle between the closest adjacent and their adjacents.
            (int) ndx = index of the vertex
            (int) ndxa = index of the closest adjacent
            (bool) is_acute = True if the angle is too low (< acute_thr).
            (bool) is_zigzag = True if both angle_v and angle_a are acute and
            the distance from va to the segment v-vb is lower than threshold.
            (bool) is_spike = True if is_acute and angle_a is not straight and
            the distance from va to the segment v-vb is lower than threshold.
            (Point) vx = projection of va over the segment v-vb.
        """
        (v, ndx, ndxa, ndxb, dist) = geom.closestVertex(Point(self))
        va = Point(geom.vertexAt(ndxa)) # previous vertex
        vb = Point(geom.vertexAt(ndxb)) # next vertex
        angle_v = abs(v.azimuth(va) - v.azimuth(vb))
        na = angle_v if angle_v < 180 else 360 - angle_v
        is_acute = na < acute_thr
        if not is_acute:
            return angle_v, None, ndx, None, is_acute, False, False, None
        dist_a = math.sqrt(va.sqrDist(v))
        dist_b = math.sqrt(vb.sqrDist(v))
        if dist_a > dist_b: # set va as the closest adjacent
            vc = va
            dist_c = dist_a
            va = vb
            dist_a = dist_b
            ndxa = ndxb
            vb = vc
            dist_b = dist_c
        angle_a = Point(va).get_angle(geom)
        c = abs(math.sin(math.radians(angle_v))) * dist_a
        is_zigzag = angle_a < acute_thr and c < threshold
        is_spike = abs(180 - angle_a) > straight_thr and c < threshold
        if is_zigzag:
            return (
                angle_v, angle_a, ndx, ndxa,
                is_acute, is_zigzag, is_spike, None,
            )
        gamma = abs(90 + angle_v - angle_a)
        dx = abs(dist_a * (
            math.cos(math.radians(angle_v)) + math.tan(math.radians(gamma)
        ) * math.sin(math.radians(angle_v))))
        x = v.x() + (vb.x() - v.x()) * dx / dist_b
        y = v.y() + (vb.y() - v.y()) * dx / dist_b
        vx = Point(x, y)
        return angle_v, angle_a, ndx, ndxa, is_acute, is_zigzag, is_spike, vx
