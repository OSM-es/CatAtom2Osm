import logging

from qgis.core import QgsFeature, QgsGeometry, QgsPointXY

from catatom2osm.config import app_name
from catatom2osm.geo.types import WKBMultiPolygon, WKBPolygon
from catatom2osm.report import instance as report

log = logging.getLogger(app_name)


class Geometry(object):
    """Methods for QGIS 2-3 compatibility and geometry utilities"""

    @staticmethod
    def fromPointXY(point):
        try:
            return QgsGeometry.fromPointXY(QgsPointXY(point))
        except (AttributeError, NameError):
            return QgsGeometry.fromPoint(point)

    @staticmethod
    def fromMultiPointXY(mp):
        try:
            return QgsGeometry.fromMultiPointXY([QgsPointXY(p) for p in mp])
        except AttributeError:
            return QgsGeometry.fromMultiPoint(mp)

    @staticmethod
    def fromPolygonXY(polygon):
        try:
            return QgsGeometry.fromPolygonXY(
                [[QgsPointXY(p) for p in r] for r in polygon]
            )
        except AttributeError:
            return QgsGeometry.fromPolygon(polygon)

    @staticmethod
    def fromMultiPolygonXY(mp):
        try:
            return QgsGeometry.fromMultiPolygonXY(
                [[[QgsPointXY(p) for p in r] for r in t] for t in mp]
            )
        except AttributeError:
            return QgsGeometry.fromMultiPolygon(mp)

    @staticmethod
    def get_multipolygon(feature_or_geometry):
        """Returns feature geometry always as a multipolygon"""
        if isinstance(feature_or_geometry, QgsFeature):
            geom = feature_or_geometry.geometry()
        else:
            geom = feature_or_geometry
        if geom.wkbType() == WKBPolygon:
            return [geom.asPolygon()]
        return geom.asMultiPolygon()

    @staticmethod
    def get_outer_rings(feature_or_geometry):
        """Returns feature geometry as a multipolygon without inner rings"""
        mp = Geometry.get_multipolygon(feature_or_geometry)
        return [[t[0]] for t in mp]

    @staticmethod
    def get_vertices_list(feature):
        """Returns list of all distinct vertices in feature geometry"""
        return [
            point
            for part in Geometry.get_multipolygon(feature)
            for ring in part
            for point in ring[0:-1]
        ]

    @staticmethod
    def get_outer_vertices(feature):
        """
        Returns list of all distinct vertices in feature geometry outer rings
        """
        return [
            point
            for part in Geometry.get_multipolygon(feature)
            for point in part[0][0:-1]
        ]

    @staticmethod
    def merge_adjacent_polygons(feature):
        """
        Merge adjacent polygons in a feature geometry
        Returns true if geometry is changed
        """
        if feature.geometry().wkbType() != WKBMultiPolygon:
            return False
        mp = Geometry.get_multipolygon(feature)
        if len(mp) < 2:
            return False
        else:
            geom = None
            for p in mp:
                g = Geometry.fromPolygonXY(p)
                ng = g if geom is None else geom.combine(g)
                if ng.isGeosValid():
                    geom = ng
            if geom is not None:
                feature.setGeometry(geom)
        return geom.isGeosValid()

    @staticmethod
    def merge_adjacent_features(group):
        """Combine all geometries in group of features"""
        geom = False
        for p in group:
            g = p.geometry()
            if g.isGeosValid():
                geom = geom.combine(g) if geom else g
            else:
                msg = _("The geometry of zone '%s' is not valid") % p["label"]
                log.warning(msg)
                report.warnings.append(msg)
        return geom

    @staticmethod
    def is_valid(geom):
        return geom.isGeosValid() and len(Geometry.get_multipolygon(geom)) > 0
