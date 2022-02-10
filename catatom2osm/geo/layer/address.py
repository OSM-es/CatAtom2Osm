import logging
import os
from collections import defaultdict

from qgis.core import QgsField, QgsFields
from qgis.PyQt.QtCore import QVariant

from catatom2osm import csvtools, config, hgwnames, translate
from catatom2osm.geo import BUFFER_SIZE
from catatom2osm.geo.aux import get_attributes
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.base import BaseLayer
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.types import WKBPoint
from catatom2osm.report import instance as report

log = logging.getLogger(config.app_name)


class AddressLayer(BaseLayer):
    """Class for address"""

    def __init__(self, path="Point", baseName="address", providerLib="memory",
            source_date=None):
        super(AddressLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('spec', QVariant.String, len=254),
                QgsField('designator', QVariant.String, len=254),
                QgsField('TN_text', QVariant.String, len=254),
                QgsField('postCode', QVariant.Int),
                QgsField('image', QVariant.String, len=254),
                QgsField('task', QVariant.String, len=254),
                QgsField('PD_id', QVariant.String, len=254),
                QgsField('TN_id', QVariant.String, len=254),
                QgsField('AU_id', QVariant.String, len=254)
            ])
            self.updateFields()
        self.rename = {'spec': 'specification'}
        self.resolve = {
            'PD_id': ('component_href', r'[\w\.]+PD[\.0-9]+'),
            'TN_id': ('component_href', r'[\w\.]+TN[\.0-9]+'),
            'AU_id': ('component_href', r'[\w\.]+AU[\.0-9]+')
        }
        self.source_date = source_date

    @staticmethod
    def create_shp(name, crs, fields=QgsFields(), geom_type=WKBPoint):
        BaseLayer.create_shp(name, crs, fields, geom_type)

    @staticmethod
    def is_address(feature):
        """Address features have '.' but not '_' in its localId field"""
        return '.' in feature['localId'] and '_' not in feature['localId']

    @staticmethod
    def get_id(feat):
        """Trim to parcel id"""
        return feat['localId'].split('_')[0].split('.')[-1]

    def to_osm(self, data=None, tags={}, upload='never'):
        """Export to OSM"""
        return super(AddressLayer, self).to_osm(translate.address_tags, data,
            tags=tags, upload=upload)

    def conflate(self, current_address):
        """
        Delete address existing in current_address

        Args:
            current_address (OSM): dataset
        """
        to_clean = [feat.id() for feat in self.getFeatures() \
            if feat['TN_text'] + feat['designator'] in current_address]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Refused %d addresses because they exist in OSM") % len(to_clean))
            report.refused_addresses = len(to_clean)
        to_clean = [feat.id() for feat in self.search("designator = '%s'" \
                                                      % config.no_number)]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Deleted %d addresses without house number") % len(to_clean))
            report.addresses_without_number = len(to_clean)

    def get_highway_names(self, highway=None):
        """
        Returns a dictionary with the translation for each street name.

        Args:
            highway (HighwayLayer): Current OSM highway data for conflation.
            If highway is None, only parse names.
        Returns:
            (dict) highway names translations
        """
        if highway is None or highway.featureCount() == 0:
            highway_names = {f['TN_text']: hgwnames.parse(f['TN_text']) \
                for f in self.getFeatures()}
        else:
            highway_names = defaultdict(list)
            index = highway.get_index()
            features = {feat.id(): feat for feat in highway.getFeatures()}
            for f in self.getFeatures():
                highway_names[f['TN_text']].append(f.geometry().asPoint())
            for name, points in highway_names.items():
                bbox = Geometry.fromMultiPointXY(points).boundingBox()
                bbox.grow(config.bbox_buffer * 100000)
                choices = [features[fid]['name'] for fid in index.intersects(bbox)]
                highway_names[name] = hgwnames.match(name, choices)
        return highway_names

    def get_image_links(self):
        to_change = {}
        for feat in self.getFeatures():
            url = config.cadastre_doc_url.format(feat['localId'][-14:])
            feat['image'] = url
            to_change[feat.id()] = get_attributes(feat)
        self.writer.changeAttributeValues(to_change)

    def remove_address_wo_building(self, buildings):
        """Remove address without associated building."""
        bu_refs = [
            f['localId'] for f in buildings.getFeatures()
            if buildings.is_building(f)
        ]
        to_clean = [
            f.id() for f in self.getFeatures()
            if self.get_id(f) not in bu_refs
        ]
        if to_clean:
            #TODO report
            self.writer.deleteFeatures(to_clean)
            msg = _("Removed %d addresses without building")
            log.debug(msg, len(to_clean))
