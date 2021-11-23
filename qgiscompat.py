#Retro compatibility for QGIS2

from qgis.core import (
    QgsCoordinateTransform, QgsProject, QgsCoordinateReferenceSystem
)
try:
    from qgis.PyQt.QtCore import QVariant
except ImportError:
    from PyQt4.QtCore import QVariant
try:
    from qgis.core import QgsWkbTypes
    WKBMultiPolygon = QgsWkbTypes.MultiPolygon
    WKBPolygon = QgsWkbTypes.Polygon
    WKBPoint = QgsWkbTypes.Point
except ImportError:
    from qgis.core import QGis
    WKBMultiPolygon = QGis.WKBMultiPolygon
    WKBPolygon = QGis.WKBPolygon
    WKBPoint = QGis.WKBPoint
try:
    from qgis.core import QgsPointXY
    Qgs2DPoint = QgsPointXY
except ImportError:
    from qgis.core import QgsPoint
    Qgs2DPoint = QgsPoint

def ggs2coordinate_transform(src_crs, target_crs):
    try:
        return QgsCoordinateTransform(src_crs, target_crs, QgsProject.instance())
    except TypeError:
        return QgsCoordinateTransform(src_crs, target_crs)

def QgsCoordinateReferenceSystem_fromEpsgId(epsg_id):
    try:
        return QgsCoordinateReferenceSystem.fromEpsgId(epsg_id)
    except AttributeError:
        return QgsCoordinateReferenceSystem(epsg_id)
