from qgis.core import (QgsCoordinateReferenceSystem, QgsFeature, QgsField,
                       QgsFields, QgsGeometry, QgsPoint)
from qgis.PyQt.QtCore import QVariant

from catatom2osm.geo.layer.base import BaseLayer


class HighwayLayer(BaseLayer):
    """Class for OSM highways"""

    def __init__(self, path="LineString", baseName="highway",
            providerLib="memory"):
        super(HighwayLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes([
                QgsField('name', QVariant.String, len=254),
            ])
            self.updateFields()
        self.setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))

    def read_from_osm(self, data):
        """Get features from a osm dataset"""
        to_add = []
        for r in data.relations:
            for m in r.members:
                if m.type=='way' and 'name' in r.tags:
                    m.element.tags['name'] = r.tags['name']
        for w in data.ways:
            if 'name' in w.tags:
                points = [QgsPoint(n.x, n.y) for n in w.nodes]
                geom = QgsGeometry.fromPolyline(points)
                feat = QgsFeature(QgsFields(self.fields()))
                feat.setGeometry(geom)
                feat.setAttribute("name", w.tags['name'])
                to_add.append(feat)
        self.writer.addFeatures(to_add)
