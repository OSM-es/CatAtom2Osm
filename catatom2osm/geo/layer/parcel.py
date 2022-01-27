import logging

from qgis.core import QgsFeature, QgsFeatureRequest, QgsField, QgsGeometry
from qgis.PyQt.QtCore import QVariant

from catatom2osm import config
from catatom2osm.geo.aux import merge_groups
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.cons import ConsLayer
from catatom2osm.geo.layer.polygon import PolygonLayer

log = logging.getLogger(config.app_name)


class ParcelLayer(PolygonLayer):
    """Class for cadastral parcels"""

    def __init__(
        self,
        path="Polygon",
        baseName="cadastralparcel",
        providerLib="memory",
        source_date=None,
    ):
        super(ParcelLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('label', QVariant.String, len=254),
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

    def get_groups_with_context(self, buildings):
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

    def merge_by_adjacent_buildings(self, buildings):
        """
        Merge parcels with buildings sharing walls with buildings of another
        parcel.
        """
        pa_groups, pa_refs, geometries = (
            self.get_groups_with_context(buildings)
        )
        count_adj = 0
        count_com = 0
        to_change = {}
        to_clean = []
        for group in pa_groups:
            group = list(group)
            count_adj += len(group)
            geom = geometries[group[0]]
            max_area = geom.area()
            max_fid = group[0]
            for fid in group[1:]:
                geom = geom.combine(geometries[fid])
                if geom.area() > max_area:
                    max_area = geom.area()
                    max_fid = fid
            to_change[max_fid] = geom
            count_com += 1
            to_clean += [fid for fid in group if fid != max_fid]
        tasks = {}
        for i, group in enumerate(pa_groups):
            for fid in group:
                localid = pa_refs.get(fid, fid)
                target_id = pa_refs[list(to_change.keys())[i]]
                if target_id != localid:
                    tasks[localid] = target_id
        if to_clean:
            self.writer.changeGeometryValues(to_change)
            self.writer.deleteFeatures(to_clean)
            msg = _("%d adjacent polygons merged into %d polygons in '%s'")
            log.debug(msg, count_adj, count_com, self.name())
        return tasks
