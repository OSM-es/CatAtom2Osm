import logging
from collections import defaultdict

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

    def merge_by_adjacent_buildings(self, buildings):
        """
        Merge parcels with buildings sharing walls with buildings of another
        parcel.
        """
        pa_groups, pa_refs, geometries = (
            self.get_groups_by_adjacent_buildings(buildings)
        )
        area = lambda fid: geometries[fid].area()
        to_change = self.merge_geometries(
            pa_groups, geometries, area, True, False
        )
        tasks = {}
        for i, group in enumerate(pa_groups):
            for fid in group:
                localid = pa_refs.get(fid, fid)
                target_id = pa_refs[list(to_change.keys())[i]]
                if target_id != localid:
                    tasks[localid] = target_id
        return tasks
