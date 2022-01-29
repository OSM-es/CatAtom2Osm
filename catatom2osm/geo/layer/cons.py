import logging
import os
from collections import defaultdict

from qgis.core import QgsFeatureRequest, QgsField, QgsGeometry
from qgis.PyQt.QtCore import QVariant

from catatom2osm import config, csvtools, translate
from catatom2osm.geo import BUFFER_SIZE, SIMPLIFY_BUILDING_PARTS
from catatom2osm.geo.aux import get_attributes, is_inside
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.point import Point
from catatom2osm.geo.types import WKBPolygon
from catatom2osm.geo.layer.polygon import PolygonLayer
from catatom2osm.report import instance as report

log = logging.getLogger(config.app_name)


class ConsLayer(PolygonLayer):
    """Class for constructions"""

    def __init__(self, path="MultiPolygon", baseName="building",
                 providerLib="memory", source_date=None):
        super(ConsLayer, self).__init__(path, baseName, providerLib)
        if self.fields().isEmpty():
            self.writer.addAttributes([
                QgsField('localId', QVariant.String, len=254),
                QgsField('condition', QVariant.String, len=254),
                QgsField('image', QVariant.String, len=254),
                QgsField('currentUse', QVariant.String, len=254),
                QgsField('bu_units', QVariant.Int),
                QgsField('dwellings', QVariant.Int),
                QgsField('lev_above', QVariant.Int),
                QgsField('lev_below', QVariant.Int),
                QgsField('nature', QVariant.String, len=254),
                QgsField('task', QVariant.String, len=254),
                QgsField('fixme', QVariant.String, len=254),
                QgsField('layer', QVariant.Int),
            ])
            self.updateFields()
        self.rename = {
            'condition': 'conditionOfConstruction',
            'image': 'documentLink',
            'bu_units': 'numberOfBuildingUnits',
            'dwellings': 'numberOfDwellings',
            'lev_above': 'numberOfFloorsAboveGround',
            'lev_below': 'numberOfFloorsBelowGround',
            'nature': 'constructionNature'
        }
        self.source_date = source_date

    @staticmethod
    def is_building(feature):
        """Building features have not any underscore in its localId field"""
        return '_' not in feature['localId']

    @staticmethod
    def is_part(feature):
        """Part features have '_part' in its localId field"""
        return '_part' in feature['localId']

    @staticmethod
    def is_pool(feature):
        """Pool features have '_PI.' in its localId field"""
        return '_PI.' in feature['localId']

    @staticmethod
    def get_id(feat):
        """Trim to parcel id"""
        return feat['localId'].split('_')[0].split('.')[-1]

    def explode_multi_parts(self, address=False):
        request = QgsFeatureRequest()
        if address:
            refs = {self.get_id(ad) for ad in address.getFeatures()}
            fids = [f.id() for f in self.getFeatures() if
                    f['localId'] not in refs]
            request.setFilterFids(fids)
        super(ConsLayer, self).explode_multi_parts(request)

    def to_osm(self, data=None, tags={}, upload='never'):
        """Export to OSM"""
        return super(ConsLayer, self).to_osm(translate.building_tags, data,
                                             tags=tags, upload=upload)

    def index_of_parts(self):
        """ Index parts of building by building localid. """
        parts = defaultdict(list)
        for part in self.search("regexp_match(localId, '_part')"):
            localId = self.get_id(part)
            parts[localId].append(part)
        return parts

    def index_of_pools(self):
        """ Index pools in building parcel by building localid. """
        pools = defaultdict(list)
        for pool in self.search("regexp_match(localId, '_PI')"):
            localId = self.get_id(pool)
            pools[localId].append(pool)
        return pools

    def index_of_building_and_parts(self):
        """
        Constructs some utility dicts.
        buildings index building by localid (call before explode_multi_parts).
        parts index parts of building by building localid.
        """
        buildings = defaultdict(list)
        parts = defaultdict(list)
        for feature in self.getFeatures():
            if self.is_building(feature):
                buildings[feature['localId']].append(feature)
            elif self.is_part(feature):
                localId = self.get_id(feature)
                parts[localId].append(feature)
        return (buildings, parts)

    def remove_outside_parts(self):
        """
        Remove parts without levels above ground.
        Remove parts outside the outline of it building.
        Precondition: Called before merge_greatest_part.
        """
        to_clean_o = []
        to_clean_b = []
        to_add = []
        buildings = {f['localId']: f for f in self.getFeatures() if
                     self.is_building(f)}
        pbar = self.get_progressbar(_("Remove outside parts"),
                                    self.featureCount())
        for feat in self.getFeatures():
            if self.is_part(feat):
                ref = self.get_id(feat)
                if feat['lev_above'] == 0 and feat['lev_below'] != 0:
                    to_clean_b.append(feat.id())
                elif ref in buildings:
                    bu = buildings[ref]
                    if not is_inside(feat, bu):
                        to_clean_o.append(feat.id())
            pbar.update()
        pbar.close()
        if len(to_clean_o) + len(to_clean_b) > 0:
            self.writer.deleteFeatures(to_clean_o + to_clean_b)
        if len(to_clean_o) > 0:
            log.debug(_("Removed %d building parts outside the outline"),
                      len(to_clean_o))
            report.outside_parts = len(to_clean_o)
        if len(to_clean_b) > 0:
            log.debug(
                _("Deleted %d building parts with no floors above ground"),
                len(to_clean_b))
            report.underground_parts = len(to_clean_b)
        if to_add:
            self.writer.addFeatures(to_add)
            log.debug(_("Generated %d building outlines"), len(to_add))
            report.new_outlines = len(to_add)

    def get_parts(self, outline, parts):
        """
        Given a building outline and its parts, for the parts inside the
        outline returns a dictionary of parts for levels, the maximum and
        minimum levels
        """
        max_level = 0
        min_level = 0
        parts_for_level = defaultdict(list)
        for part in parts:
            if is_inside(part, outline):
                level = (part['lev_above'] or 0, part['lev_below'] or 0)
                if level[0] > max_level: max_level = level[0]
                if level[1] > min_level: min_level = level[1]
                parts_for_level[level].append(part)
        return parts_for_level, max_level, min_level

    def merge_adjacent_parts(self, outline, parts):
        """
        Given a building outline and its parts, for the parts inside the
        outline:

          * Translates the maximum values of number of levels above and below
            ground to the outline and optionally deletes all the parts in
            that level.

          * Merges the adjacent parts in each level.
        """
        to_clean = []
        to_clean_g = []
        to_change = {}
        to_change_g = {}
        parts_for_level, max_level, min_level = self.get_parts(outline, parts)
        parts_area = 0
        outline['lev_above'] = max_level
        outline['lev_below'] = min_level
        building_area = round(outline.geometry().area(), 0)
        for (level, parts) in parts_for_level.items():
            check_area = False
            for part in parts:
                part_area = part.geometry().area()
                parts_area += part_area
                if round(part_area, 0) > building_area:
                    part['fixme'] = _('This part is bigger than its building')
                    to_change[part.id()] = get_attributes(part)
                    check_area = True
            if check_area:
                continue
            if len(parts_for_level) == 1 or (
                    level == (max_level, min_level) and SIMPLIFY_BUILDING_PARTS
            ):
                to_clean = [p.id() for p in
                            parts_for_level[max_level, min_level]]
            else:
                geom = Geometry.merge_adjacent_features(parts)
                poly = Geometry.get_multipolygon(geom)
                if len(poly) < len(parts):
                    for (i, part) in enumerate(parts):
                        if i < len(poly):
                            g = Geometry.fromPolygonXY(poly[i])
                            to_change_g[part.id()] = g
                        else:
                            to_clean_g.append(part.id())
        if len(parts_for_level) > 1 and round(parts_area, 0) != building_area:
            outline['fixme'] = _(
                "Building parts don't fill the building outline")
        to_change[outline.id()] = get_attributes(outline)
        return to_clean, to_clean_g, to_change, to_change_g

    def remove_inner_rings(self, feat1, feat2):
        """
        Auxiliary method to remove feat1 of its inner rings if equals to feat2
        Returns True if feat1 must be deleted and new geometry if any ring is
        removed.
        """
        poly = Geometry.get_multipolygon(feat1)[0]
        geom2 = Geometry.fromPolygonXY(Geometry.get_multipolygon(feat2)[0])
        delete = False
        new_geom = None
        delete_rings = []
        for i, ring in enumerate(poly):
            if Geometry.fromPolygonXY([ring]).equals(geom2):
                if i == 0:
                    delete = True
                    break
                else:
                    delete_rings.append(i)
        if delete_rings:
            new_poly = [ring for i, ring in enumerate(poly) \
                        if i not in delete_rings]
            new_geom = Geometry().fromPolygonXY(new_poly)
        return delete, new_geom

    def merge_building_parts(self):
        """
        Detect pools contained in a building and assign layer=1.
        Detect buildings/parts with geometry equals to a pool geometry and
        delete them.
        Detect inner rings of buildings/parts with geometry equals to a pool
        geometry and remove them.
        Apply merge_adjacent_parts to each set of building and its parts.
        """
        parts = self.index_of_parts()
        pools = self.index_of_pools()
        to_clean = []
        to_change = {}
        to_change_g = {}
        buildings_in_pools = 0
        levels_to_outline = 0
        parts_merged_to_building = 0
        adjacent_parts_deleted = 0
        pools_on_roofs = 0
        visited_parcels = set()
        t_buildings = self.count("not regexp_match(localId, '_')")
        pbar = self.get_progressbar(_("Merge building parts"), t_buildings)
        for building in self.search("not regexp_match(localId, '_')"):
            ref = building['localId']
            it_pools = pools[ref]
            it_parts = parts[ref]
            for pool in it_pools:
                if pool['layer'] != 1 and is_inside(pool, building):
                    pool['layer'] = 1
                    to_change[pool.id()] = get_attributes(pool)
                    pools_on_roofs += 1
                del_building, new_geom = self.remove_inner_rings(building, pool)
                if del_building:
                    to_clean.append(building.id())
                    buildings_in_pools += 1
                    break
                if new_geom:
                    to_change_g[building.id()] = QgsGeometry(new_geom)
                if ref not in visited_parcels:
                    for part in frozenset(it_parts):
                        del_part, new_geom = self.remove_inner_rings(part, pool)
                        if del_part:
                            to_clean.append(part.id())
                            it_parts.remove(part)
                            if part in parts[ref]:
                                parts[ref].remove(part)
                            adjacent_parts_deleted += 1
                        elif new_geom:
                            to_change_g[part.id()] = QgsGeometry(new_geom)
            visited_parcels.add(ref)
            cn, cng, ch, chg = self.merge_adjacent_parts(building, it_parts)
            to_clean += cn + cng
            to_change.update(ch)
            to_change_g.update(chg)
            levels_to_outline += len(ch)
            parts_merged_to_building += len(cn)
            adjacent_parts_deleted += len(cng)
            pbar.update()
        pbar.close()
        if to_change:
            self.writer.changeAttributeValues(to_change)
        if to_change_g:
            self.writer.changeGeometryValues(to_change_g)
        if to_clean:
            self.writer.deleteFeatures(to_clean)
        if pools_on_roofs:
            log.debug(_("Located %d swimming pools over a building"),
                      pools_on_roofs)
            report.pools_on_roofs = pools_on_roofs
        if buildings_in_pools:
            log.debug(
                _("Deleted %d buildings coincidents with a swimming pool"),
                buildings_in_pools)
            report.buildings_in_pools = buildings_in_pools
        if levels_to_outline:
            log.debug(_("Translated %d level values to the outline"),
                      levels_to_outline)
        if parts_merged_to_building:
            log.debug(_("Merged %d building parts to the outline"),
                      parts_merged_to_building)
            report.parts_to_outline = parts_merged_to_building
        if adjacent_parts_deleted:
            log.debug(_("Merged %d adjacent parts"), adjacent_parts_deleted)
            report.adjacent_parts = adjacent_parts_deleted

    def clean(self):
        """
        Delete invalid geometries and close vertices, add topological points,
        merge building parts and simplify vertices.
        """
        self.delete_invalid_geometries()
        self.topology()
        self.merge_building_parts()
        self.simplify()

    def move_entrance(
            self, ad, ad_buildings, ad_parts, to_move, to_insert,
            parents_per_vx,
    ):
        """
        Auxiliary method to move entrance to the nearest building and part.
        Don't move and the entrance specification is changed if the new
        position is not enough close ('remote'), is a corner ('corner'),
        is in an inner ring ('inner') or is in a wall shared with another
        building ('shared').
        """
        point = ad.geometry().asPoint()
        distance = 9E9
        for bu in ad_buildings:
            bg = bu.geometry()
            d, c, v = bg.closestSegmentWithContext(point)[:3]
            if d < distance:
                (building, distance, closest, vertex) = (bu, d, c, v)
        bg = building.geometry()
        bid = building.id()
        va = Point(bg.vertexAt(vertex - 1))
        vb = Point(bg.vertexAt(vertex))
        if distance > config.addr_thr ** 2:
            ad['spec'] = 'remote'
        elif vertex > len(Geometry.get_multipolygon(bg)[0][0]):
            ad['spec'] = 'inner'
        elif (
                closest.sqrDist(va) < config.entrance_thr ** 2
                or closest.sqrDist(vb) < config.entrance_thr ** 2
        ):
            ad['spec'] = 'corner'
        elif PolygonLayer.is_shared_segment(parents_per_vx, va, vb, bid):
            ad['spec'] = 'shared'
        else:
            dg = Geometry.fromPointXY(closest)
            to_move[ad.id()] = dg
            bg.insertVertex(closest.x(), closest.y(), vertex)
            to_insert[bid] = QgsGeometry(bg)
            building.setGeometry(bg)
            for part in ad_parts:
                pg = part.geometry()
                r = Geometry.get_multipolygon(pg)[0][0]
                for i in range(len(r) - 1):
                    vpa = Point(pg.vertexAt(i))
                    vpb = Point(pg.vertexAt(i + 1))
                    if va in (vpa, vpb) and vb in (vpa, vpb):
                        pg.insertVertex(closest.x(), closest.y(), i + 1)
                        to_insert[part.id()] = QgsGeometry(pg)
                        part.setGeometry(pg)
                        break

    def move_address(self, address):
        """
        Try to move each entrance address to the nearest point in the outline
        of its associated building (same cadastral reference). Non entrance
        addresses ends in the building outline when CatAtom2Osm.merge_address
        is called. Delete the address if the number of associated buildings
        is 0 or greater than 1 for non entrance addresses.
        """
        to_change = {}
        to_move = {}
        to_insert = {}
        to_clean = []
        mp = 0
        oa = 0
        (buildings, parts) = self.index_of_building_and_parts()
        exp = "NOT(localId ~ '_')"
        ppv, geometries = self.get_parents_per_vertex_and_geometries(exp)
        pbar = self.get_progressbar(_("Move addresses"), address.featureCount())
        for ad in address.getFeatures():
            refcat = self.get_id(ad)
            building_count = len(buildings.get(refcat, []))
            ad_buildings = buildings[refcat]
            ad_parts = parts[refcat]
            if building_count == 0:
                to_clean.append(ad.id())
                oa += 1
            else:
                if ad['spec'] == 'Entrance':
                    self.move_entrance(
                        ad, ad_buildings, ad_parts, to_move, to_insert, ppv,
                    )
                if ad['spec'] != 'Entrance' and building_count > 1:
                    to_clean.append(ad.id())
                    mp += 1
                if ad['spec'] != 'Parcel' and building_count == 1:
                    to_change[ad.id()] = get_attributes(ad)
            if len(to_insert) > BUFFER_SIZE:
                self.writer.changeGeometryValues(to_insert)
                to_insert = {}
            pbar.update()
        pbar.close()
        address.writer.changeAttributeValues(to_change)
        address.writer.changeGeometryValues(to_move)
        if len(to_insert) > 0:
            self.writer.changeGeometryValues(to_insert)
        msg = _("Moved %d addresses to entrance, %d specification changed")
        log.debug(msg, len(to_move), len(to_change))
        if len(to_clean) > 0:
            address.writer.deleteFeatures(to_clean)
        if oa > 0:
            msg = _("Deleted %d addresses without associated building")
            log.debug(msg, oa)
            report.pool_addresses = oa
        if mp > 0:
            msg = _("Refused %d addresses belonging to multiple buildings")
            log.debug(msg, mp)
            report.multiple_addresses = mp

    def validate(self, max_level, min_level):
        """Put fixmes to buildings with not valid geometry, too small or big.
        Returns distribution of floors"""
        to_change = {}
        for feat in self.getFeatures():
            geom = feat.geometry()
            errors = geom.validateGeometry()
            if errors:
                feat['fixme'] = _('GEOS validation') + ': ' + \
                                '; '.join([e.what() for e in errors])
                to_change[feat.id()] = get_attributes(feat)
            if ConsLayer.is_building(feat):
                localid = feat['localId']
                if isinstance(feat['lev_above'], int) and feat['lev_above'] > 0:
                    max_level[localid] = feat['lev_above']
                if isinstance(feat['lev_below'], int) and feat['lev_below'] > 0:
                    min_level[localid] = feat['lev_below']
                if feat.id() not in to_change:
                    area = geom.area()
                    if area < config.warning_min_area:
                        feat['fixme'] = _("Check, area too small")
                        to_change[feat.id()] = get_attributes(feat)
                    if area > config.warning_max_area:
                        feat['fixme'] = _("Check, area too big")
                        to_change[feat.id()] = get_attributes(feat)
        if to_change:
            self.writer.changeAttributeValues(to_change)

    def conflate(self, current_bu_osm, delete=True):
        """
        Removes from current_bu_osm the buildings that don't have conflicts.
        If delete=False, only mark buildings with conflicts
        """
        if len(current_bu_osm.elements) == 0:
            return
        index = self.get_index()
        geometries = {f.id(): QgsGeometry(f.geometry()) for f in
                      self.getFeatures()}
        num_buildings = 0
        conflicts = 0
        to_clean = set()
        pbar = self.get_progressbar(_("Conflate"), len(current_bu_osm.elements))
        for el in current_bu_osm.elements:
            poly = None
            is_pool = 'leisure' in el.tags and el.tags[
                'leisure'] == 'swimming_pool'
            is_building = 'building' in el.tags
            if el.type == 'way' and el.is_closed() and (is_building or is_pool):
                poly = [[map(Point, el.geometry())]]
            elif el.type == 'relation' and (is_building or is_pool):
                poly = [[map(Point, w)] for w in el.outer_geometry()]
            if poly:
                num_buildings += 1
                geom = Geometry().fromMultiPolygonXY(poly)
                if geom is None or not geom.isGeosValid():
                    msg = _("OSM building with id %s is not valid") % el.fid
                    pbar.clear()
                    log.warning(msg)
                    report.warnings.append(msg)
                else:
                    fids = index.intersects(geom.boundingBox())
                    conflict = False
                    for fid in fids:
                        fg = geometries[fid]
                        if geom.contains(fg) or fg.contains(
                                geom) or geom.overlaps(fg):
                            conflict = True
                            conflicts += 1
                            break
                    if delete and not conflict:
                        to_clean.add(el)
                    if not delete and conflict:
                        el.tags['conflict'] = 'yes'
            pbar.update()
        pbar.close()
        for el in to_clean:
            current_bu_osm.remove(el)
        log.debug(_("Detected %d conflicts in %d buildings/pools from OSM"),
                  conflicts, num_buildings)
        report.osm_buildings = num_buildings
        report.osm_building_conflicts = conflicts
        return len(to_clean) > 0
