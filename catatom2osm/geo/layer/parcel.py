import logging
from collections import defaultdict

from qgis.core import QgsFeature, QgsFeatureRequest, QgsField, QgsGeometry
from qgis.PyQt.QtCore import QVariant

from catatom2osm import config
from catatom2osm.geo.aux import get_attributes, merge_groups
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.polygon import PolygonLayer

log = logging.getLogger(config.app_name)


class ParcelLayer(PolygonLayer):
    """Class for cadastral parcels"""

    def __init__(
        self,
        path="MultiPolygon",
        baseName="cadastralparcel",
        providerLib="memory",
        source_date=None,
    ):
        super(ParcelLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('parts', QVariant.Int),
            ])
            self.updateFields()
        self.rename = {'localId': 'inspireId_localId'}
        self.source_date = source_date

    def delete_void_parcels(self, buildings):
        """Remove parcels without buildings (or pools)."""
        exp = "NOT(localId ~ 'part')"
        bu_refs = [ConsLayer.get_id(f) for f in buildings.search(exp)]
        to_clean = [
            f.id() for f in self.getFeatures() if f['localId'] not in bu_refs
        ]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Removed %d void parcels"), len(to_clean))

    def create_missing_parcels(self, buildings):
        """Creates fake parcels for buildings not contained in any."""
        pa_refs = [f['localId'] for f in self.getFeatures()]
        to_add = {}
        exp = "NOT(localId ~ 'part')"
        for bu in buildings.getFeatures(exp):
            ref = buildings.get_id(bu)
            if ref not in pa_refs:
                mp = Geometry.get_outer_rings(bu)
                bu_geom = Geometry.fromMultiPolygonXY(mp)
                if ref in to_add:
                    parcel = to_add[ref]
                    pa_geom = bu_geom.combine(parcel.geometry())
                    parcel.setGeometry(pa_geom)
                else:
                    parcel = QgsFeature(self.fields())
                    parcel['localId'] = ref
                    parcel.setGeometry(bu_geom)
                to_add[ref] = parcel
        if to_add:
            self.writer.addFeatures(to_add.values())
            log.debug(_("Added %d missing parcels"), len(to_add))

    def get_groups_by_adjacent_buildings(self, buildings):
        """
        Get grupos of ids of parcels with buildings sharing walls with
        buildings of another parcel.
        """
        exp = "NOT(localId ~ 'part')"
        bu_groups, __ = buildings.get_adjacents_and_geometries(exp)
        bu_refs = {f.id(): ConsLayer.get_id(f) for f in buildings.search(exp)}
        geometries = {}
        pa_ids = {}
        pa_refs = {}
        for f in self.getFeatures():
            geometries[f.id()] = QgsGeometry(f.geometry())
            pa_ids[f['localId']] = f.id()
            pa_refs[f.id()] = f['localId']
        adjs = []
        for group in bu_groups:
            pids = set()
            for bid in group:
                ref = bu_refs[bid]
                pids.add(pa_ids[ref])
            adjs.append(pids)
        pa_groups = merge_groups(adjs)
        return pa_groups, pa_refs, geometries

    def update_parts_count(self, pa_groups, pa_refs, parts_count):
        tasks = {}
        self.startEditing()
        for group in pa_groups:
            pc = 0
            targetid = pa_refs[group[0]]
            for fid in group:
                localid = pa_refs[fid]
                tasks[localid] = targetid
                pc += parts_count[localid]
            fnx = self.writer.fieldNameIndex('parts')
            self.changeAttributeValue(group[0], fnx, pc)
        self.commitChanges()
        return tasks

    def merge_by_adjacent_buildings(self, buildings):
        """
        Merge parcels with buildings sharing walls with buildings of another
        parcel.
        """
        parts_count = self.count_parts(buildings)
        pa_groups, pa_refs, geometries = (
            self.get_groups_by_adjacent_buildings(buildings)
        )
        area = lambda fid: geometries[fid].area()
        self.merge_geometries(pa_groups, geometries, area, True, False)
        tasks = self.update_parts_count(pa_groups, pa_refs, parts_count)
        return tasks

    def count_parts(self, buildings):
        """Adds count of parts in parcel field"""
        parts = []
        parts_count = defaultdict(int)
        exp = "localId ~ '_'"
        for f in buildings.getFeatures(exp):
            parts_count[buildings.get_id(f)] += 1
            parts.append(buildings.get_id(f))
        for f in buildings.getFeatures():
            if buildings.get_id(f) not in parts:
                parts_count[buildings.get_id(f)] += 1
        parts_count = dict(parts_count)
        to_change = {}
        for f in self.getFeatures():
            f['parts'] = parts_count[f['localId']]
            to_change[f.id()] = get_attributes(f)
        self.writer.changeAttributeValues(to_change)
        return parts_count

    def get_groups_by_parts_count(self, buildings, max_parts, buffer):
        """
        Get groups of ids of near parcels with less than max_parts
        """
        parts_count = {}
        geometries = {}
        pa_refs = {}
        for pa in self.getFeatures():
            geometries[pa.id()] = QgsGeometry(pa.geometry())
            parts_count[pa['localId']] = pa['parts']
            pa_refs[pa.id()] = pa['localId']
        pa_groups = []
        visited = []
        index = self.get_index()
        for pa in self.getFeatures():
            if pa.id() in visited:
                continue
            pc = pa['parts']
            geom = geometries[pa.id()]
            bbox = geom.boundingBox().buffered(buffer)
            fids = index.intersects(bbox)
            candidates = [
                fid for fid in fids
                if parts_count[pa_refs[fid]] <= max_parts - pc
            ]
            centro = geom.centroid()
            distance = lambda fid: centro.distance(geometries[fid].centroid())
            candidates = sorted(candidates, key=distance)
            group = []
            pcsum = 0
            for fid in candidates:
                pc = parts_count[pa_refs[fid]]
                if pcsum + pc <= max_parts and fid not in visited:
                    visited.append(fid)
                    group.append(fid)
                    pcsum += pc
            if group:
                pa_groups.append(group)
        return pa_groups, pa_refs, geometries, parts_count

    def merge_by_parts_count(self, buildings, max_parts, buffer):
        """Merge parcels in groups with less than max_parts"""
        pa_groups, pa_refs, geometries, parts_count = (
            self.get_groups_by_parts_count(buildings, max_parts, buffer)
        )
        self.merge_geometries(pa_groups, geometries, None, False, False)
        tasks = self.update_parts_count(pa_groups, pa_refs, parts_count)
        return tasks
