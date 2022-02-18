import logging
from collections import Counter, defaultdict

from qgis.core import QgsFeature, QgsFeatureRequest, QgsFields, QgsGeometry
from tqdm import tqdm

from catatom2osm import config
from catatom2osm.geo import BUFFER_SIZE
from catatom2osm.geo.aux import is_inside, is_inside_area, merge_groups
from catatom2osm.geo.debug import DebugWriter
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.layer.base import BaseLayer
from catatom2osm.geo.point import Point
from catatom2osm.geo.types import WKBPolygon
from catatom2osm.report import instance as report

log = logging.getLogger(config.app_name)


class PolygonLayer(BaseLayer):
    """Base class for polygon layers"""

    def __init__(self, path, baseName, providerLib = "ogr"):
        super(PolygonLayer, self).__init__(path, baseName, providerLib)
        # Distance in meters to merge nearest vertex
        self.dup_thr = config.dup_thr
        # Threshold in meters for cathetus reduction
        self.cath_thr = config.dist_thr
        # Threshold in degrees from straight angle to delete a vertex
        self.straight_thr = config.straight_thr
        # Threshold for topological points
        self.dist_thr = config.dist_thr

    def get_area(self):
        """Returns total area"""
        return sum([f.geometry().area() for f in self.getFeatures()])

    def is_inside(self, feature):
        """Returns first feature of this layer that have feature inside"""
        for feat in self.getFeatures():
            if is_inside(feature, feat):
                return feat
        return None

    def is_inside_area(self, feature):
        """Returns first feature of this layer that have feature inside"""
        for feat in self.getFeatures():
            if is_inside_area(feature, feat):
                return feat
        return None

    def explode_multi_parts(self, request=QgsFeatureRequest()):
        """
        Creates a new WKBPolygon feature for each part of any WKBMultiPolygon
        feature in request. This avoid relations with many 'outer' members in
        OSM data set. From this moment, localId will not be a unique identifier
        for buildings.
        """
        to_clean = []
        to_add = []
        msg = _("Explode multi parts")
        pbar = self.get_progressbar(msg, self.featureCount())
        for feature in self.getFeatures(request):
            mp = Geometry.get_multipolygon(feature)
            if len(mp) > 1:
                for part in mp:
                    feat = QgsFeature(feature)
                    feat.setGeometry(Geometry.fromPolygonXY(part))
                    to_add.append(feat)
                to_clean.append(feature.id())
            pbar.update()
        pbar.close()
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            self.writer.addFeatures(to_add)
            log.debug(_("%d multi-polygons splitted into %d polygons in "
                "the '%s' layer"), len(to_clean), len(to_add),
                self.name())
            report.values['multipart_geoms_' + self.name()] = len(to_clean)
            report.values['exploded_parts_' + self.name()] = len(to_add)

    @staticmethod
    def is_shared_segment(parents_per_vx, va, vb, feature_id):
        """
        Given a dictionary of parents per vertex check if segment va-vb in
        geometry of feature with id 'feature_id' is shared with another
        geometry.
        """
        parents = [gid for gid in parents_per_vx[va.asWkt()] if gid != feature_id]
        parents += [gid for gid in parents_per_vx[vb.asWkt()] if gid != feature_id]
        return any([c > 1 for c in Counter(parents).values()])

    def get_parents_per_vertex_and_geometries(self, expression=''):
        """
        Returns:
            (dict) parent fids for each vertex, (dict) geometry for each fid.
        Precondition:
            Called before reproject.
        """
        parents_per_vertex = defaultdict(list)
        geometries = {}
        for feature in self.search(expression):
            geom = QgsGeometry(feature.geometry())
            geometries[feature.id()] = geom
            for point in Geometry.get_vertices_list(feature):
                parents_per_vertex[point.asWkt()].append(feature.id())
        return (parents_per_vertex, geometries)

    def get_contacts_and_geometries(self, expression=''):
        """
        Returns:
            (list) groups of polygons with at least one common node
            (dict) feature id: geometry
        """
        parents_per_vertex, geometries = (
            self.get_parents_per_vertex_and_geometries(expression)
        )
        adjs = []
        for (__, parents) in parents_per_vertex.items():
            if len(parents) > 1:
                adjs.append(parents)
        return (adjs, geometries)

    def get_adjacents_and_geometries(self, expression=''):
        """
        Returns:
            (list) groups of adjacent polygons
            (dict) feature id: geometry
        """
        parents_per_vertex, geometries = (
            self.get_parents_per_vertex_and_geometries(expression)
        )
        adjs = []
        for (wkt, parents) in parents_per_vertex.items():
            point = Point(wkt)
            if len(parents) > 1:
                for fid in parents:
                    geom = geometries[fid]
                    (point, ndx, ndxa, ndxb, dist) = geom.closestVertex(point)
                    next = Point(geom.vertexAt(ndxb))
                    parents_next = parents_per_vertex[next.asWkt()]
                    common = set(x for x in parents if x in parents_next)
                    if len(common) > 1:
                        adjs.append(common)
        adjs = list(adjs)
        groups = merge_groups(adjs)
        return (groups, geometries)

    def topology(self):
        """For each vertex in a polygon layer, adds it to nearest segments."""
        threshold = self.dist_thr # Distance threshold to create nodes
        dup_thr = self.dup_thr
        straight_thr = self.straight_thr
        tp = 0
        td = 0
        if log.app_level <= logging.DEBUG:
            debshp = DebugWriter("debug_topology.shp", self)
        geometries = {
            f.id(): QgsGeometry(f.geometry()) for f in self.getFeatures()
        }
        index = self.get_index()
        to_change = {}
        nodes = set()
        pbar = self.get_progressbar(_("Topology"), len(geometries))
        for (gid, geom) in geometries.items():
            for point in frozenset(Geometry.get_outer_vertices(geom)):
                if point not in nodes:
                    area_of_candidates = Point(point).boundingBox(threshold)
                    fids = index.intersects(area_of_candidates)
                    for fid in fids:
                        g = QgsGeometry(geometries[fid])
                        (p, ndx, ndxa, ndxb, dist_v) = g.closestVertex(point)
                        (dist_s, closest, vertex) = (
                            g.closestSegmentWithContext(point)[:3]
                        )
                        va = Point(g.vertexAt(ndxa))
                        vb = Point(g.vertexAt(ndxb))
                        note = ""
                        if dist_v == 0:
                            dist_a = va.sqrDist(point)
                            dist_b = vb.sqrDist(point)
                            if dist_a < dup_thr**2:
                                g.deleteVertex(ndxa)
                                note = "dupe refused by isGeosValid"
                                if Geometry.is_valid(g):
                                    note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                        (dist_a, va.x(), va.y(), point.x(), point.y())
                                    nodes.add(p)
                                    nodes.add(va)
                                    td += 1
                            if dist_b < dup_thr**2:
                                g.deleteVertex(ndxb)
                                note = "dupe refused by isGeosValid"
                                if Geometry.is_valid(g):
                                    note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                        (dist_b, vb.x(), vb.y(), point.x(), point.y())
                                    nodes.add(p)
                                    nodes.add(vb)
                                    td += 1
                        elif dist_v < dup_thr**2:
                            g.moveVertex(point.x(), point.y(), ndx)
                            note = "dupe refused by isGeosValid"
                            if Geometry.is_valid(g):
                                note = "Merge dup. %.10f %.5f,%.5f->%.5f,%.5f" % \
                                    (dist_v, p.x(), p.y(), point.x(), point.y())
                                nodes.add(p)
                                td += 1
                        elif dist_s < threshold**2 and closest != va and closest != vb:
                            va = Point(g.vertexAt(vertex))
                            vb = Point(g.vertexAt(vertex - 1))
                            angle = abs(point.azimuth(va) - point.azimuth(vb))
                            note = "Topo refused by angle: %.2f" % angle
                            if abs(180 - angle) <= straight_thr:
                                note = "Topo refused by insertVertex"
                                if g.insertVertex(point.x(), point.y(), vertex):
                                    note = "Topo refused by isGeosValid"
                                    if Geometry.is_valid(g):
                                        note = "Add topo %.6f %.5f,%.5f" % \
                                            (dist_s, point.x(), point.y())
                                        tp += 1
                        if note.startswith('Merge') or note.startswith('Add'):
                            to_change[fid] = g
                            geometries[fid] = g
                        if note and log.app_level <= logging.DEBUG:
                            debshp.add_point(point, note)
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeGeometryValues(to_change)
                to_change = {}
            pbar.update()
        pbar.close()
        if len(to_change) > 0:
            self.writer.changeGeometryValues(to_change)
        if td:
            log.debug(_("Merged %d close vertices in the '%s' layer"), td,
                self.name())
            report.values['vertex_close_' + self.name()] = td
        if tp:
            log.debug(_("Created %d topological points in the '%s' layer"),
                tp, self.name())
            report.values['vertex_topo_' + self.name()] = tp

    def merge_adjacent_polygons(self):
        """
        Merge adjacent polygons in each feature geometry
        """
        to_change = {}
        for feat in self.getFeatures():
            if Geometry.merge_adjacent_polygons(feat):
                to_change[feat.id()] = feat.geometry()
        if len(to_change) > 0:
            self.writer.changeGeometryValues(to_change)

    def delete_small_geometries(self):
        to_clean = []
        for feat in self.getFeatures():
            fid = feat.id()
            geom = feat.geometry()
            if geom.area() < config.min_area:
                to_clean.append(fid)
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            msg = _("Deleted %d invalid geometries in the '%s' layer")
            log.debug(msg, len(to_clean), self.name())
            report.inc('geom_invalid_' + self.name(), len(to_clean))

    def delete_invalid_geometries(self, query_small_area=lambda feat: True):
        """
        Delete invalid geometries testing if any of it acute angle vertex could
        be deleted.
        Also removes zig-zag and spike vertex (see Point.get_spike_context).
        """
        if log.app_level <= logging.DEBUG:
            debshp = DebugWriter(
                'debug_notvalid.shp', self, QgsFields(), WKBPolygon
            )
            debshp2 = DebugWriter("debug_spikes.shp", self)
        to_change = {}
        to_clean = []
        to_move = {}
        parts = 0
        rings = 0
        zz = 0
        spikes = 0
        geometries = {}
        msg = _("Delete invalid geometries")
        pbar = self.get_progressbar(msg, len(geometries))
        for feat in self.getFeatures():
            fid = feat.id()
            geom = feat.geometry()
            badgeom = False
            pn = 0
            for polygon in Geometry.get_multipolygon(geom):
                f = QgsFeature(QgsFields())
                g = Geometry.fromPolygonXY(polygon)
                if g.area() < config.min_area and query_small_area(feat):
                    parts += 1
                    geom.deletePart(pn)
                    to_change[fid] = geom
                    f.setGeometry(QgsGeometry(g))
                    if log.app_level <= logging.DEBUG:
                        debshp.addFeature(f)
                    continue
                pn += 1
                for i, ring in enumerate(polygon):
                    if badgeom: break
                    skip = False
                    for n, v in enumerate(ring[0:-1]):
                        (
                            angle_v, angle_a, ndx, ndxa,
                            is_acute, is_zigzag, is_spike, vx,
                        ) = Point(v).get_spike_context(geom)
                        if skip or not is_acute:
                            skip = False
                            continue
                        g = Geometry.fromPolygonXY([ring])
                        f.setGeometry(QgsGeometry(g))
                        g.deleteVertex(n)
                        if not g.isGeosValid() or g.area() < config.min_area:
                            if i > 0:
                                rings += 1
                                geom.deleteRing(i)
                                to_change[fid] = geom
                                if log.app_level <= logging.DEBUG:
                                    debshp.addFeature(f)
                            else:
                                badgeom = True
                                to_clean.append(fid)
                                if log.app_level <= logging.DEBUG:
                                    debshp.addFeature(f)
                            break
                        if len(ring) > 4: # (can delete vertexs)
                            va = Point(geom.vertexAt(ndxa))
                            if is_zigzag:
                                g = QgsGeometry(geom)
                                if ndxa > ndx:
                                    g.deleteVertex(ndxa)
                                    g.deleteVertex(ndx)
                                    skip = True
                                else:
                                    g.deleteVertex(ndx)
                                    g.deleteVertex(ndxa)
                                valid = g.isGeosValid()
                                if valid:
                                    geom = g
                                    zz += 1
                                    to_change[fid] = g
                                if log.app_level <= logging.DEBUG:
                                    debshp2.add_point(va, 'zza %d %d %d %f' % (fid, ndx, ndxa, angle_a))
                                    debshp2.add_point(v, 'zz %d %d %d %s' % (fid, ndx, len(ring), valid))
                            elif is_spike:
                                g = QgsGeometry(geom)
                                to_move[va] = vx #!
                                g.moveVertex(vx.x(), vx.y(), ndxa)
                                g.deleteVertex(ndx)
                                valid = g.isGeosValid()
                                if valid:
                                    spikes += 1
                                    skip = ndxa > ndx
                                    geom = g
                                    to_change[fid] = g
                                if log.app_level <= logging.DEBUG:
                                    debshp2.add_point(vx, 'vx %d %d' % (fid, ndx))
                                    debshp2.add_point(va, 'va %d %d %d %f' % (fid, ndx, ndxa, angle_a))
                                    debshp2.add_point(v, 'v %d %d %d %s' % (fid, ndx, len(ring), valid))
                geometries[fid] = geom
            if geom.area() < config.min_area and query_small_area(feat):
                to_clean.append(fid)
                if fid in to_change:
                    del to_change[fid]
            pbar.update()
        pbar.close()
        if to_move:
            for fid, geom in geometries.items():
                if fid in to_clean: continue
                n = 0
                v = Point(geom.vertexAt(n))
                while v.x() != 0 or v.y() != 0:
                    if v in to_move:
                        g = QgsGeometry(geom)
                        vx = to_move[v]
                        if log.app_level <= logging.DEBUG:
                            debshp2.add_point(v, 'mv %d %d' % (fid, n))
                            debshp2.add_point(vx, 'mvx %d %d' % (fid, n))
                        g.moveVertex(vx.x(), vx.y(), n)
                        if g.isGeosValid():
                            geom = g
                            to_change[fid] = g
                    n += 1
                    v = Point(geom.vertexAt(n))
        if to_change:
            self.writer.changeGeometryValues(to_change)
        if parts:
            msg = _("Deleted %d invalid part geometries in the '%s' layer")
            log.debug(msg, parts, self.name())
            report.values['geom_parts_' + self.name()] = parts
        if rings:
            msg = _("Deleted %d invalid ring geometries in the '%s' layer")
            log.debug(msg, rings, self.name())
            report.values['geom_rings_' + self.name()] = rings
        if to_clean:
            self.writer.deleteFeatures(to_clean)
            msg = _("Deleted %d invalid geometries in the '%s' layer")
            log.debug(msg, len(to_clean), self.name())
            report.values['geom_invalid_' + self.name()] = len(to_clean)
        if zz:
            msg = _("Deleted %d zig-zag vertices in the '%s' layer")
            log.debug(msg, zz, self.name())
            report.values['vertex_zz_' + self.name()] = zz
        if spikes:
            msg = _("Deleted %d spike vertices in the '%s' layer")
            log.debug(msg, spikes, self.name())
            report.values['vertex_spike_' + self.name()] = spikes

    def simplify(self):
        """
        Reduces the number of vertices in a polygon layer according to:

        * Delete vertex if the angle with its adjacents is near of the straight
          angle for less than 'straight_thr' degrees in all its parents.

        * Delete vertex if the distance to the segment formed by its parents is
          less than 'cath_thr' meters.
        """
        if log.app_level <= logging.DEBUG:
            debshp = DebugWriter("debug_simplify.shp", self)
        killed = 0
        to_change = {}
        # Clean non corners
        (parents_per_vertex, geometries) = (
            self.get_parents_per_vertex_and_geometries()
        )
        pbar = self.get_progressbar(_("Simplify"), len(parents_per_vertex))
        for wkt, parents in parents_per_vertex.items():
            point = Point(wkt)
            # Test if this vertex is a 'corner' in any of its parent polygons
            for fid in parents:
                geom = geometries[fid]
                (angle, is_acute, is_corner, cath) = (
                    point.get_corner_context(geom)
                )
                debmsg = "angle=%.1f, is_acute=%s, is_corner=%s, cath=%.4f" % (
                    angle, is_acute, is_corner, cath
                )
                if is_corner: break
            msg = "Keep"
            if not is_corner:
                killed += 1      # delete the vertex from all its parents.
                for fid in frozenset(parents):
                    g = QgsGeometry(geometries[fid])
                    (__, ndx, __, __, __) = g.closestVertex(point)
                    (ndxa, ndxb) = g.adjacentVertices(ndx)
                    v = g.vertexAt(ndx)
                    va = g.vertexAt(ndxa)
                    vb = g.vertexAt(ndxb)
                    invalid_ring = (v == va or v == vb or va == vb)
                    g.deleteVertex(ndx)
                    msg = "Refused"
                    if Geometry.is_valid(g) and not invalid_ring:
                        parents.remove(fid)
                        geometries[fid] = g
                        to_change[fid] = g
                        msg = "Deleted"
            if log.app_level <= logging.DEBUG:
                debshp.add_point(point, msg + ' ' + debmsg)
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeGeometryValues(to_change)
                to_change = {}
            pbar.update()
        pbar.close()
        if len(to_change) > 0:
            self.writer.changeGeometryValues(to_change)
        if killed > 0:
            log.debug(_("Simplified %d vertices in the '%s' layer"), killed,
                self.name())
            report.values['vertex_simplify_' + self.name()] = killed

    def merge_geometries(
        self, groups, geometries, sort=None, reverse=False, split=True
    ):
        """
        Merge groups of fids from geometries.

        Args:
            groups (list): groups of adjacent polygons
            geometries (dict): feature id: geometry
            sort (lambda or None): key to sort group
            reverse (bool): reverse sort if True
            split (bool): split multipart geometries if True

        Returns:
            (dict): feature id: geometry changed geometries
        """
        to_clean = []
        to_change = {}
        count_adj = 0
        count_com = 0
        for i, group in enumerate(groups):
            group = sorted(group, key=sort, reverse=reverse)
            groups[i] = group
            count_adj += len(group)
            geom = geometries[group[0]]
            for fid in group[1:]:
                geom = geom.combine(geometries[fid])
            if split:
                mp = Geometry.get_multipolygon(geom)
                for j, part in enumerate(mp):
                    g = Geometry.fromPolygonXY(part)
                    to_change[group[j]] = g
                    count_com += 1
                to_clean += group[j + 1:]
            else:
                to_change[group[0]] = geom
                count_com += 1
                to_clean += group[1:]
        if to_clean:
            self.writer.changeGeometryValues(to_change)
            self.writer.deleteFeatures(to_clean)
            msg = _("%d polygons merged into %d polygons in '%s'")
            log.debug(msg, count_adj, count_com, self.name())
        return to_change, to_clean

    def merge_adjacents(self):
        """Merge polygons with shared segments"""
        (groups, geometries) = self.get_adjacents_and_geometries()
        merge_geometries(groups, geometries)

    def difference(self, layer):
        """Calculate the difference of each geometry with those in layer"""
        geometries = {
            f.id(): QgsGeometry(f.geometry()) for f in layer.getFeatures()
        }
        index = layer.get_index()
        pbar = self.get_progressbar(_("Difference"), len(geometries))
        for feat in self.getFeatures():
            g1 = feat.geometry()
            fids = index.intersects(g1.boundingBox())
            gc = None
            for fid in fids:
                g2 = geometries[fid]
                if g2.intersects(g1):
                    if gc is None:
                        gc = QgsGeometry(g2)
                    else:
                        gc = gc.combine(g2)
                    pbar.update()
            if gc is not None:
                g1 = g1.difference(gc)
                self.writer.changeGeometryValues({feat.id(): g1})
        pbar.close()

    def clean(self):
        """Delete invalid geometries and close vertices, add topological points
        and simplify vertices."""
        self.delete_invalid_geometries()
        self.topology()
        self.simplify()
