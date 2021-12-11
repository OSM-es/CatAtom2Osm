#Retro compatibility for QGIS2

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFields,
    QgsProject,
    QgsVectorFileWriter,
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


def QgsVectorFileWriter_create(
    name, crs, fields=QgsFields(), geom_type=WKBMultiPolygon
):
    if hasattr(QgsVectorFileWriter, 'create'):
        transform_context = QgsProject.instance().transformContext()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = "ESRI Shapefile"
        save_options.fileEncoding = "UTF-8"
        writer = QgsVectorFileWriter.create(
            name, fields, geom_type, crs, transform_context, save_options
        )
    else:
        writer = QgsVectorFileWriter(
            name, 'UTF-8', fields, geom_type, crs, 'ESRI Shapefile'
        )
    return writer

def QgsVectorFileWriter_writeAsVectorFormat(layer, name, crs, driver_name):
    if hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV2'):
        transform_context = QgsProject.instance().transformContext()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = driver_name
        save_options.fileEncoding = "UTF-8"
        error = QgsVectorFileWriter.writeAsVectorFormatV2(
            layer, name, transform_context, save_options
        )
    else:
        error = QgsVectorFileWriter.writeAsVectorFormat(
            layer, name, "utf-8", crs, driver_name
        )
    return error