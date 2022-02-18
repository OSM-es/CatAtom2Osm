import logging
import os

from qgis.core import QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant

from catatom2osm import config
from catatom2osm.geo import BUFFER_SIZE
from catatom2osm.geo.aux import get_attributes, is_inside
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.polygon import PolygonLayer

log = logging.getLogger(config.app_name)

level_query = lambda f, kw: ZoningLayer.check_zone(f, kw["level"])


class ZoningLayer(PolygonLayer):
    """Class for cadastral zoning"""

    upattern = "{:05}"
    rpattern = "{:03}"

    def __init__(
        self,
        path="MultiPolygon",
        baseName="cadastralzoning",
        providerLib="memory",
        source_date=None,
    ):
        super(ZoningLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes(
                [
                    QgsField("localId", QVariant.String, len=254),
                    QgsField("label", QVariant.String, len=254),
                    QgsField("levelName", QVariant.String, len=254),
                    QgsField("zipcode", QVariant.String, len=5),
                ]
            )
            self.updateFields()
        self.rename = {
            "localId": "inspireId_localId",
            "levelName": "LocalisedCharacterString",
        }
        self.source_date = source_date
        self.task_number = 0
        self.task_pattern = self.rpattern
        if baseName == "urbanzoning":
            self.task_pattern = self.upattern

    @staticmethod
    def check_zone(feat, level=None):
        if not level:
            return True
        if feat.fieldNameIndex("levelName") < 0:
            zone_type = feat["LocalisedCharacterString"][0]
        else:
            if type(feat["levelName"]) is list:
                zone_type = feat["levelName"][0]
            zone_type = feat["levelName"].split(":")[-1][0]
        return level == zone_type

    @staticmethod
    def format_label(feature):
        """Format a zone label"""
        label = feature["label"]
        level = ZoningLayer.check_zone(feature, "M")
        pattern = ZoningLayer.upattern if level else ZoningLayer.rpattern
        try:
            label = pattern.format(int(feature["label"]))
        except:
            pass
        return label

    def append(self, layer, rename=None, resolve=None, query=level_query, **kwargs):
        """Append filtering by level: 'M' Urban, 'P' Rustic"""
        super(ZoningLayer, self).append(layer, rename, resolve, query, **kwargs)

    # TODO renovar
    def export_poly(self, filename):
        """Export as polygon file for Osmosis"""
        mun = Geometry.merge_adjacent_features([f for f in self.getFeatures()])
        mun = Geometry.get_multipolygon(mun)
        with open(filename, "w") as fo:
            fo.write("admin_boundary\n")
            i = 0
            for part in mun:
                for j, ring in enumerate(part):
                    i += 1
                    prefix = "!" if j > 0 else ""
                    fo.write(prefix + str(i) + "\n")
                    for p in ring:
                        fo.write("%f %f\n" % (p.x(), p.y()))
                    fo.write("END\n")
            fo.write("END\n")
        return
