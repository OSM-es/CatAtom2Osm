import logging
import os

from qgis.core import QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant

from catatom2osm import config
from catatom2osm.geo import BUFFER_SIZE
from catatom2osm.geo.aux import get_attributes, is_inside, is_inside_area
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.polygon import PolygonLayer

log = logging.getLogger(config.app_name)


class ZoningLayer(PolygonLayer):
    """Class for cadastral zoning"""

    upattern = '{:05}'
    rpattern = '{:03}'

    def __init__(
        self,
        path="MultiPolygon",
        baseName="cadastralzoning",
        providerLib="memory",
        source_date=None
    ):
        super(ZoningLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('label', QVariant.String, len=254),
                QgsField('levelName', QVariant.String, len=254),
                QgsField('zipcode', QVariant.String, len=5),
            ])
            self.updateFields()
        self.rename = {
            'localId': 'inspireId_localId',
            'levelName': 'LocalisedCharacterString',
        }
        self.source_date = source_date
        self.task_number = 0
        self.task_pattern = self.rpattern
        if baseName == 'urbanzoning':
            self.task_pattern = self.upattern

    @staticmethod
    def check_zone(feat, level=None):
        if not level:
            return True
        if feat.fieldNameIndex('levelName') < 0:
            zone_type = feat['LocalisedCharacterString'][0]
        else:
            if type(feat['levelName']) is list:
                zone_type = feat['levelName'][0]
            zone_type = feat['levelName'].split(':')[-1][0]
        return level == zone_type

    @staticmethod
    def format_label(feature):
        """Format a zone label"""
        label = feature['label']
        level = ZoningLayer.check_zone(feature, 'M')
        pattern = ZoningLayer.upattern if level else ZoningLayer.rpattern
        try:
            label = pattern.format(int(feature['label']))
        except:
            pass
        return label

    def set_tasks(self, zip_code):
        """Assings a unique task label to each zone"""
        to_change = {}
        for zone in self.getFeatures():
            zone['label'] = self.format_label(zone)
            zone['zipcode'] = zip_code
            to_change[zone.id()] = get_attributes(zone)
        self.writer.changeAttributeValues(to_change)

    def append(self, layer, level=None):
        """Append features. Split multipolygon geometries.

        Args:
            layer(QgsVectorLayer): cadastralzoning GML source
            level(str): 'P' (rustic polygon), 'M' (urban block) or None for both
        """
        self.setCrs(layer.crs())
        total = 0
        to_add = []
        multi = 0
        final = 0
        pbar = self.get_progressbar(_("Append"), layer.featureCount())
        for feature in layer.getFeatures():
            if self.check_zone(feature, level):
                feat = self.copy_feature(feature)
                geom = feature.geometry()
                mp = Geometry.get_multipolygon(geom)
                if len(mp) > 1:
                    for part in mp:
                        f = QgsFeature(feat)
                        f.setGeometry(Geometry.fromPolygonXY(part))
                        to_add.append(f)
                        final += 1
                    multi += 1
                    total += 1
                elif len(mp) == 1:
                    to_add.append(feat)
                    total += 1
            if len(to_add) > BUFFER_SIZE:
                self.writer.addFeatures(to_add)
                to_add = []
            pbar.update()
        pbar.close()
        if len(to_add) > 0:
            self.writer.addFeatures(to_add)
        if total:
            log.debug (_("Loaded %d features in '%s' from '%s'"), total,
                self.name(), layer.name())
        if multi:
            log.debug(_("%d multi-polygons splitted into %d polygons in "
                "the '%s' layer"), multi, final, self.name())

    def export_poly(self, filename):
        """Export as polygon file for Osmosis"""
        mun = Geometry.merge_adjacent_features([f for f in self.getFeatures()])
        mun = Geometry.get_multipolygon(mun)
        with open(filename, 'w') as fo:
            fo.write('admin_boundary\n')
            i = 0
            for part in mun:
                for j, ring in enumerate(part):
                    i += 1
                    prefix = '!' if j > 0 else ''
                    fo.write(prefix + str(i) + '\n')
                    for p in ring:
                        fo.write('%f %f\n' % (p.x(), p.y()))
                    fo.write('END\n')
            fo.write('END\n')
        return

    def remove_outside_features(self, layer=None, skip=[]):
        """
        Remove any zone not contained in layer features except if its label
        is in skip list.
        """
        split = None
        if layer:
            split = Geometry.merge_adjacent_features(
                [f for f in layer.getFeatures()]
            )
            if layer.crs() != self.crs():
                crs_transform = self.get_crs_transform(layer.crs(), self.crs())
                split.transform(crs_transform)
        to_clean = []
        fcount = self.featureCount()
        for feat in self.getFeatures():
            geom = feat.geometry()
            if feat['label'] not in skip:
                if split:
                    inter = split.intersection(geom)
                    if inter.area() / geom.area() < 0.5:
                        to_clean.append(feat.id())
                else:
                    to_clean.append(feat.id())
        if len(to_clean):
            self.writer.deleteFeatures(to_clean)
            msg = _("%s: Removed %d of %d features.")
            log.debug(msg, self.name(), len(to_clean), fcount)

    def set_zone(self, layer):
        """
        Assigns to each feature of layer the label of the zone that contains it
        """
        index = layer.get_index()
        features = {f.id(): f for f in layer.getFeatures()}
        for zone in self.getFeatures():
            to_change = {}
            label = self.format_label(zone)
            fids = index.intersects(zone.geometry().boundingBox())
            for fid in fids:
                pa = features[fid]
                if is_inside_area(pa, zone):
                    if pa['zone'] is None:
                        pa['zone'] = label
                        to_change[fid] = get_attributes(pa)
            if to_change:
                layer.writer.changeAttributeValues(to_change)

    def get_labels(self, labels, gml):
        """
        Builds in labels an index of gml features localId vs the label of the
        zone in witch it is contained. If the feature geometry overlaps many
        zones, takes the zone with the largest intersection.
        """
        index = self.get_index()
        features = {f.id(): f for f in self.getFeatures()}
        pbar = gml.get_progressbar(_("Labeling"), gml.featureCount())
        for feat in gml.getFeatures():
            localid = ConsLayer.get_id(feat)
            label = labels.get(localid, None)
            if label is None or label == 'missing':
                if ConsLayer.is_part(feat):
                    continue  # exclude parts without building
                fids = index.intersects(feat.geometry().boundingBox())
                zones = [
                    features[fid] for fid in fids
                    if is_inside(feat, features[fid])
                ]
                if len(zones) == 0:
                    label = 'missing'
                else:
                    label = self.format_label(zones[0])
                    geom = feat.geometry()
                    parea = zones[0].geometry().intersection(geom).area()
                    for z in zones[1:]:
                        area = z.geometry().intersection(geom).area()
                        if area > parea:
                            parea = area
                            label = self.format_label(z)
                labels[localid] = label
            pbar.update()
        pbar.close()
