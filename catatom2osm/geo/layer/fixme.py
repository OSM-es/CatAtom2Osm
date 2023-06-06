from qgis.core import QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant

from catatom2osm.geo.layer.base import BaseLayer


class FixmeLayer(BaseLayer):
    """Class for fixmes."""

    def __init__(self, path="Point", baseName="fixme", providerLib="memory"):
        super(FixmeLayer, self).__init__(path, baseName, providerLib)
        self.writer.addAttributes([QgsField("fixme", QVariant.String, len=254)])
        self.updateFields()

    def add_fixme(self, feat):
        """Add geometry centroid to the layer with the attribute fixme."""
        target = QgsFeature(self.fields())
        geom = feat.geometry().centroid()
        target.setGeometry(geom)
        target.setAttribute("fixme", feat["fixme"])
        self.writer.addFeature(target)
