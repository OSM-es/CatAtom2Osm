import logging
from collections import defaultdict

from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsRectangle
from qgis.PyQt.QtCore import QVariant

from catatom2osm import config
from catatom2osm.geo.aux import get_attributes, is_inside_area, merge_groups
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.polygon import PolygonLayer

log = logging.getLogger(config.app_name)


class ParcelLayer(PolygonLayer):
    """Class for cadastral parcels."""

    def __init__(
        self,
        mun_code,
        path="MultiPolygon",
        baseName="cadastralparcel",
        providerLib="memory",
        source_date=None,
    ):
        super(ParcelLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes(
                [
                    QgsField("localId", QVariant.String, len=14),
                    QgsField("parts", QVariant.Int),
                    QgsField("zone", QVariant.String, len=5),
                    QgsField("type", QVariant.String, len=10),
                    QgsField("muncode", QVariant.String, len=5),
                ]
            )
            self.updateFields()
        self.mun_code = mun_code
        self.rename = {"localId": "inspireId_localId"}
        self.source_date = source_date
        self.mun_code = mun_code

    def delete_void_parcels(self, *sources):
        """Remove parcels without buildings (or pools)/addresses."""
        refs = []
        for source in sources:
            if source is not None:
                for f in source.getFeatures():
                    refs.append(ConsLayer.get_id(f))
        to_clean = [f.id() for f in self.getFeatures() if f["localId"] not in refs]
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            log.debug(_("Removed %d void parcels"), len(to_clean))

    def create_missing_parcels(self, *sources, split=None):
        """Create fake parcels for buildings not contained in any."""
        pa_refs = [f["localId"] for f in self.getFeatures()]
        to_add = {}
        for source in sources:
            if source is None:
                continue
            for feat in source.getFeatures():
                ref = ConsLayer.get_id(feat)
                if ref not in pa_refs:
                    mp = Geometry.get_outer_rings(feat)
                    geom = Geometry.fromMultiPolygonXY(mp)
                    if ref in to_add:
                        parcel = to_add[ref]
                        geom = parcel.geometry().combine(geom)
                        parcel.setGeometry(geom)
                        to_add[ref] = parcel
                    elif split is None or split.is_inside_area(geom):
                        parcel = QgsFeature(self.fields())
                        parcel["localId"] = ref
                        parcel.setGeometry(geom)
                        to_add[ref] = parcel
        if to_add:
            self.writer.addFeatures(to_add.values())
            log.debug(_("Added %d missing parcels"), len(to_add))

    def set_muncode(self, muncode):
        """Assign to each parcel the code of the municipality."""
        to_change = {}
        for pa in self.getFeatures():
            pa["muncode"] = muncode
            to_change[pa.id()] = get_attributes(pa)
        if to_change:
            self.writer.changeAttributeValues(to_change)

    def set_zones(self, zoning):
        """Assign to each parcel the label of the zone that contains it."""
        index = zoning.get_index()
        features = {f.id(): f for f in zoning.getFeatures()}
        to_change = {}
        for pa in self.getFeatures():
            if pa["zone"] is None:
                c = pa.geometry().centroid().asPoint()
                bb = QgsRectangle(c, c)
                fids = index.intersects(bb)
                for fid in fids:
                    zone = features[fid]
                    label = zoning.format_label(zone)
                    pa_label = self.get_zone(pa)
                    if pa_label == label or is_inside_area(pa, zone):
                        if str(label) == "inf":
                            label = pa_label
                        pa["zone"] = label
                        to_change[pa.id()] = get_attributes(pa)
                        break
        msg = _("Assigned %d zones from %s to parcels")
        log.debug(msg, len(to_change), self.sourceName())
        if to_change:
            self.writer.changeAttributeValues(to_change)

    def set_missing_zones(self):
        """Assign label from cadastral reference if no zone exists."""
        to_change = {}
        m = 0
        for pa in self.getFeatures():
            if pa["zone"] is None:
                m += 1
                pa["zone"] = self.get_zone(pa)
            pa["type"] = _("Rustic") if len(pa["zone"]) == 3 else _("Urban")
            pa["type"] = pa["type"].replace("ú", "&uacute;")
            to_change[pa.id()] = get_attributes(pa)
        if m:
            log.debug(_("There are %d parcels without zone"), m)
        self.writer.changeAttributeValues(to_change)

    def get_groups_by_adjacent_buildings(self, buildings):
        """Get groups of parcel ids with buildings sharing walls in another parcel."""
        exp = "NOT(localId ~ 'part')"
        bu_groups, __ = buildings.get_contacts_and_geometries(exp)
        bu_refs = {f.id(): ConsLayer.get_id(f) for f in buildings.search(exp)}
        geometries = {}
        pa_ids = {}
        pa_refs = {}
        pa_zone = {}
        for f in self.getFeatures():
            geometries[f.id()] = QgsGeometry(f.geometry())
            pa_ids[f["localId"]] = f.id()
            pa_refs[f.id()] = f["localId"]
            pa_zone[f.id()] = self.get_zone(f)
        adjs = defaultdict(list)
        for group in bu_groups:
            pids = set()
            for bid in group:
                ref = bu_refs[bid]
                pids.add(pa_ids[ref])
            k = "-".join(set([pa_zone[fid] for fid in pids]))
            adjs[k].append(pids)
        mz_groups = {k for k in adjs.keys() if "-" in k}
        mz_groups |= {z for k in mz_groups for z in k.split("-")}
        pa_groups = merge_groups([adj for z in mz_groups for adj in adjs[z]])
        for z, adj in adjs.items():
            if z not in mz_groups:
                if len(adj) == 1:
                    pa_groups.append(adj[0])
                else:
                    for group in merge_groups(adj):
                        pa_groups.append(group)
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
            fnx = self.writer.fieldNameIndex("parts")
            self.changeAttributeValue(group[0], fnx, pc)
        self.commitChanges()
        return tasks

    def merge_by_adjacent_buildings(self, buildings):
        """Merge parcels with buildings sharing walls with in another parcel."""

        def area(fid):
            return geometries[fid].area()

        parts_count = self.count_parts(buildings)
        pa_groups, pa_refs, geometries = self.get_groups_by_adjacent_buildings(
            buildings
        )
        self.merge_geometries(pa_groups, geometries, area, True, False)
        tasks = self.update_parts_count(pa_groups, pa_refs, parts_count)
        return tasks

    def count_parts(self, buildings):
        """Add count of parts in parcel field."""
        parts_count = defaultdict(int)
        for f in buildings.getFeatures():
            parts_count[buildings.get_id(f)] += 1
        to_change = {}
        for f in self.getFeatures():
            f["parts"] = parts_count[f["localId"]]
            to_change[f.id()] = get_attributes(f)
        self.writer.changeAttributeValues(to_change)
        return dict(parts_count)

    def get_zone(self, feat):
        zone = feat["zone"]
        if zone is None:
            localid = feat["localId"]
            zone = localid[0:5]
            if zone == self.mun_code:
                zone = localid[6:9]
        return zone

    def get_groups_by_parts_count(self, max_parts, buffer):
        """Get groups of ids of near parcels with less than max_parts."""

        def distance(fid):
            return centro.distance(geometries[fid].centroid())

        parts_count = {}
        geometries = {}
        pa_refs = {}
        zoning = defaultdict(list)
        for pa in self.getFeatures():
            geometries[pa.id()] = QgsGeometry(pa.geometry())
            parts_count[pa["localId"]] = pa["parts"]
            pa_refs[pa.id()] = pa["localId"]
            zoning[self.get_zone(pa)].append(pa.id())
        pa_groups = []
        visited = []
        for pa in self.getFeatures():
            if pa.id() in visited:
                continue
            pc = pa["parts"]
            geom = geometries[pa.id()]
            centro = geom.centroid()
            label = self.get_zone(pa)
            candidates = [
                fid
                for fid in zoning[label]
                if parts_count[pa_refs[fid]] <= max_parts - pc
                and distance(fid) < buffer
            ]
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

    def merge_by_parts_count(self, max_parts, buffer):
        """Merge parcels in groups with less than max_parts."""
        pa_groups, pa_refs, geometries, parts_count = self.get_groups_by_parts_count(
            max_parts, buffer
        )
        self.merge_geometries(pa_groups, geometries, None, False, False)
        tasks = self.update_parts_count(pa_groups, pa_refs, parts_count)
        return tasks

    def clean(self):
        """
        Clean geometries.

        Delete invalid geometries and close vertices, add topological points
        and simplify vertices.
        """
        self.delete_invalid_geometries()
        self.topology()
        self.simplify()
