import os

from qgis.core import QgsFeature, QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant

from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.base import BaseLayer
from catatom2osm.geo.types import WKBPoint


class DebugWriter():
    """A QgsVectorFileWriter for debugging purposess."""

    def __init__(
        self, filename, layer, driver_name="ESRI Shapefile", geom_type=WKBPoint
    ):
        """
        Args:
            filename (str): File name of this layer
            layer (QgsVectorLayer): A layer to test.
            driver_name (str): Defaults to ESRI Shapefile.
        """
        fpath = os.path.join(
            os.path.dirname(layer.dataProvider().dataSourceUri()), filename
        )
        fields = QgsFields()
        fields.append(QgsField("note", QVariant.String, len=100))
        writer = BaseLayer.get_writer(fpath, layer.crs(), fields, geom_type)
        self.fields = fields
        self.writer = writer

    def add_point(self, point, note=None):
        """Adds a point to the layer with the attribute note."""
        feat = QgsFeature(QgsFields(self.fields))
        geom = Geometry.fromPointXY(point)
        feat.setGeometry(geom)
        if note:
            feat.setAttribute("note", note[:254])
        return self.addFeature(feat)

    def addFeature(self, *args, **kwargs):
        self.writer.addFeature(*args, **kwargs)
