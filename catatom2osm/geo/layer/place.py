from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsPoint,
)
from qgis.PyQt.QtCore import QVariant

from catatom2osm.geo.layer.base import BaseLayer


class PlaceLayer(BaseLayer):
    """Class for OSM places."""

    def __init__(self, path="Point", baseName="highway", providerLib="memory"):
        super(PlaceLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes(
                [
                    QgsField("name", QVariant.String, len=254),
                ]
            )
            self.updateFields()
        self.setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))

    def read_from_osm(self, data):
        """Get features from a osm dataset."""
        to_add = []
        for elem in data.elements:
            if "place" in elem.tags:
                feat = QgsFeature(QgsFields(self.fields()))
                feat.setAttribute("name", elem.tags["name"])
                geom = False
                if elem.type == "node":
                    geom = QgsGeometry.fromPointXY(QgsPointXY(elem.x, elem.y))
                elif elem.type == "way":
                    points = [QgsPoint(n.x, n.y) for n in elem.nodes]
                    geom = QgsGeometry.fromPolyline(points).centroid()
                elif elem.type == "relation":
                    xp = []
                    yp = []
                    for m in elem.members:
                        if m.type == "way" and m.role == "outer":
                            xp += [n.x for n in m.element.nodes]
                            yp += [n.y for n in m.element.nodes]
                    if [xp]:
                        xm = sum(xp) / len(xp)
                        ym = sum(yp) / len(yp)
                        geom = QgsGeometry.fromPointXY(QgsPointXY(xm, ym))
                if geom:
                    feat.setGeometry(geom)
                    to_add.append(feat)
        self.writer.addFeatures(to_add)
