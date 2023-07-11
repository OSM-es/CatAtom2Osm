"""Main application processes."""
import codecs
import gzip
import io
import logging
import os
import shutil
from collections import defaultdict
from glob import glob
from zipfile import ZIP_DEFLATED, ZipFile

# isort: off
from past.builtins import basestring  # NOQA: F401 - qgis/utils.py:744: Warning

# isort: on
import qgis.utils
from osgeo import gdal
from qgis.core import QgsApplication, QgsGeometry, QgsVectorLayer

from catatom2osm import cdau  # NOQA: F401 - Used in get_auxiliary_addresses
from catatom2osm import boundary, catatom, cbcn, config, csvtools, geo, osmxml, overpass
from catatom2osm.exceptions import CatIOError, CatValueError
from catatom2osm.report import instance as report

qgis.utils.uninstallErrorHook()
qgis_utils = getattr(qgis.utils, "QGis", getattr(qgis.utils, "Qgis", None))

log = logging.getLogger(config.app_name)
if config.silence_gdal:
    gdal.PushErrorHandler("CPLQuietErrorHandler")

tasks_folder = "tasks"


class QgsSingleton(QgsApplication):
    """Keep a unique instance of QGIS for the application (and tests)."""

    _qgs = None

    def __new__(cls):
        if QgsSingleton._qgs is None:
            # Init qGis API
            QgsSingleton._qgs = QgsApplication([], False)
            qgis_prefix = os.getenv("QGISHOME")
            if qgis_prefix:
                QgsApplication.setPrefixPath(qgis_prefix, True)
            QgsApplication.initQgis()
            # sets GDAL to convert xlink references to fields but not resolve
            gdal.SetConfigOption("GML_ATTRIBUTES_TO_OGR_FIELDS", "YES")
            gdal.SetConfigOption("GML_SKIP_RESOLVE_ELEMS", "ALL")
        return QgsSingleton._qgs


class CatAtom2Osm(object):
    """Main application class."""

    def __init__(self, a_path, options):
        """
        Application constructor.

        Args:
            a_path (str): Directory where the source files are located.
            options (dict): Dictionary of options.
        """
        self.options = options
        self.cat = catatom.Reader(a_path)
        self.path = self.cat.path
        report.clear(options=self.options.args, mun_code=self.cat.zip_code)
        if config.report_system_info:
            report.qgs_version = qgis_utils.QGIS_VERSION
            report.gdal_version = gdal.__version__
            log.debug(_("Initialized QGIS %s API"), report.qgs_version)
            log.debug(_("Using GDAL %s"), report.gdal_version)
        if not options.building and not options.address:
            options.address = True
            options.building = True
        opt = ""
        if not self.options.address:
            opt = "-b"
        elif not self.options.building:
            opt = "-d"
        self.tasks_folder = tasks_folder + opt
        self.tasks_path = self.cat.get_path(self.tasks_folder)
        if self.options.zoning:
            self.options.address = False
        fn = self.options.split or ""
        bkp_dir = os.path.splitext(os.path.basename(fn))[0]
        self.bkp_path = self.cat.get_path(bkp_dir)
        self.highway_names_path = self.cat.get_path("highway_names.csv")
        self.is_new = not os.path.exists(self.highway_names_path)
        self.source = "building"
        self.aux_path = os.path.join(os.path.dirname(self.path), config.aux_path)
        if self.options.address and not self.options.building:
            self.source = "address"

    @staticmethod
    def create_and_run(a_path, options):
        app = CatAtom2Osm(a_path, options)
        app.run()
        app.exit()

    @staticmethod
    def get_task_comment(label):
        """Return comment for task with this label."""
        comment = " ".join(
            (
                config.changeset_tags["comment"],
                report.mun_code,
                report.mun_name,
                label,
            )
        )
        return comment

    def run(self):
        """Launch the app processing."""
        if self.options.municipality:
            self.get_municipality()
            return
        if self.options.comment:
            self.add_comments()
            return
        self.get_boundary()
        self.get_split()
        if self.options.info:
            self.get_parcel()
            self.get_building()
            self.get_address()
            report.tags_for_info()
            fn = f"_{self.options.split}" if self.options.split else ""
            report.export(self.cat.get_path(f"info{fn}.json"))
            return
        if self.options.address and not self.is_new:
            log.info(_("Resume processing '%s'"), report.mun_code)
            self.resume_address()
        else:
            log.info(_("Start processing '%s'"), report.mun_code)
            if report.get("split_name"):
                log.info(_("Administrative boundary: '%s'"), report.split_name)
            elif self.options.split:
                log.info(_("Split: '%s'"), self.options.split)
            self.get_parcel()
            self.get_building()
            self.get_zoning()
            if self.options.zoning:
                self.export_poly()
            self.process_building()
            self.process_parcel()
            if self.options.address:
                self.get_address()
                self.stop_address()
                return
        if self.options.address:
            self.process_address()
            self.address.reproject()
        if not self.options.zoning:
            self.building.reproject()
            self.process_tasks(getattr(self, self.source))
        self.output_zoning()
        self.finish()

    def get_municipality(self):
        """Create municipality <mun_code>.geojson geometry from cadastral zoning."""
        parcel_gml = self.cat.read("cadastralzoning")
        municipality = geo.ZoningLayer(baseName="rusticzoning")
        q = lambda f, kw: municipality.check_zone(f, kw["level"])
        municipality.append(parcel_gml, query=q, level="P")
        municipality.clean()
        municipality.reproject()
        municipality.merge_adjacents()
        self.export_layer(
            municipality, self.cat.zip_code + ".geojson", target_crs_id=4326
        )
        return

    def add_comments(self):
        """Recover missing task files metadata after JOSM editing."""
        folder = os.path.basename(self.tasks_path)
        report_path = self.cat.get_path("report.json")
        if not os.path.exists(report_path):
            log.info(_("No report found"))
            return
        report.from_file(report_path)
        tasks = 0
        for fn in os.listdir(self.tasks_path):
            if fn.endswith(".osm") or fn.endswith(".osm.gz"):
                tasks += 1
                label = os.path.basename(fn).split(".")[0]
                data = self.read_osm(folder, fn)
                fixmes = sum([1 for e in data.elements if "fixme" in e.tags])
                if fixmes > 0:
                    log.warning(_("Check %d fixme tags"), fixmes)
                oldtags = dict(data.tags)
                data.tags.update(config.changeset_tags)
                data.tags["comment"] = self.get_task_comment(label)
                data.tags["generator"] = report.app_version
                if "building_date" in report.values:
                    data.tags["source:date"] = report.building_date
                if "address_date" in report.values:
                    data.tags["source:date:addr"] = report.address_date
                if data.tags != oldtags:
                    self.write_osm(data, folder, fn)
        if not tasks:
            log.info(_("No tasks found"))

    def get_split(self):
        """Get boundary file for splitting."""
        self.split = None
        if self.options.split:
            fn = self.options.split
            if not os.path.exists(fn):
                if "." not in os.path.basename(fn):
                    fn += ".osm"
                if not os.path.exists(fn) and fn == os.path.basename(fn):
                    fn = self.cat.get_path(fn)
            if fn.endswith(".osm"):
                fn += "|layername=multipolygons"
            split = geo.BaseLayer(fn, "zoningsplit", "ogr")
            if split.isValid():
                report.split_file = self.options.split
            else:
                msg = "Can't open %s" % self.options.split
                fn = self.options.split
                if os.path.basename(fn) == fn and "." not in fn:
                    report.split_id = fn
                    fn = boundary.get_boundary(self.path, self.boundary_search_area, fn)
                    name = fn.replace(".osm|layername=multipolygons", "")
                    report.split_name = name.split("/")[-1].replace("_", " ")
                    split = geo.BaseLayer(fn, "zoningsplit", "ogr")
                    if not split.isValid():
                        raise CatIOError(msg)
                else:
                    raise CatIOError(msg)
            self.split = geo.PolygonLayer("MultiPolygon", "split", "memory")
            q = lambda f, __: f.geometry().wkbType() == geo.types.WKBMultiPolygon
            self.split.append(split, query=q)
            if self.split.featureCount() == 0:
                msg = _("'%s' does not include any polygon") % self.options.split
                raise CatValueError(msg)

    def get_parcel(self):
        """Get parcels dataset."""
        parcel_gml = self.cat.read("cadastralparcel")
        report.cat_mun = self.cat.cat_mun
        self.parcel = geo.ParcelLayer(self.cat.zip_code)
        self.parcel.source_date = parcel_gml.source_date
        q = None
        if self.split:
            if self.split.crs() != parcel_gml.crs():
                self.split.reproject(parcel_gml.crs())
            q = lambda f, __: self.split.is_inside_area(f)
        elif self.options.parcel:
            localid = self.options.parcel[0]
            try:
                pa = next(parcel_gml.search(f"localId = '{localid}'"))
            except StopIteration:
                msg = _("Parcel '%s' does not exists") % localid
                raise CatValueError(msg)
            bb = pa.geometry().boundingBox().buffered(config.parcel_buffer)
            g = QgsGeometry.fromRect(bb)
            q = lambda f, __: geo.tools.is_inside(f, g)
        self.parcel_query = q
        self.parcel.append(parcel_gml, query=q)
        del parcel_gml
        if self.parcel.featureCount() == 0:
            raise CatValueError(_("No parcels data"))

    def get_building(self):
        """Merge building, parts and pools."""
        building_gml = self.cat.read("building")
        other_gml = self.cat.read("otherconstruction", True)
        if not self.options.info:
            self.parcel.delete_void_parcels(building_gml, other_gml)
            self.parcel.clean()
        self.parcel.create_missing_parcels(building_gml, other_gml, split=self.split)
        self.tasks = {f["localId"]: f["localId"] for f in self.parcel.getFeatures()}
        self.building = geo.ConsLayer()
        self.building.source_date = building_gml.source_date
        q = None
        if self.split or self.options.parcel:
            q = lambda f, kw: self.building.get_id(f) in kw["keys"]
        self.building.append(building_gml, query=q, keys=self.tasks.keys())
        del building_gml
        inbu = self.building.featureCount()
        if inbu == 0:
            raise CatValueError(_("No buildings data"))
        if other_gml:
            self.building.append(other_gml, query=q, keys=self.tasks.keys())
            del other_gml
        if self.options.address and not self.options.building:
            return
        inpo = self.building.featureCount() - inbu
        part_gml = self.cat.read("buildingpart")
        self.building.append(part_gml, query=q, keys=self.tasks.keys())
        del part_gml
        if self.options.building:
            report.building_date = self.building.source_date
            report.inp_features = self.building.featureCount()
            report.inp_buildings = inbu
            report.inp_pools = inpo
            report.inp_parts = report.inp_features - inbu - inpo

    def process_tasks(self, source):
        """Convert to osm for each task."""
        if not os.path.exists(self.tasks_path):
            os.makedirs(self.tasks_path)
        tasks = self.get_tasks(source)
        tasks_r = 0
        tasks_u = 0
        to_clean = []
        to_change = {}
        report.parcel_parts = config.parcel_parts
        report.parcel_dist = config.parcel_dist
        for pa in self.parcel.getFeatures():
            label = pa["localId"]
            task = tasks.get(label, None)
            if task is None:
                to_clean.append(pa.id())
                continue
            if len(pa["zone"]) == 3:
                tasks_r += 1
            else:
                tasks_u += 1
            comment = self.get_task_comment(label)
            task_osm = task.to_osm(upload="yes", tags={"comment": comment})
            if self.options.address and self.options.building:
                self.merge_address(task_osm, self.address_osm)
            if self.options.address:
                report.address_stats(task_osm)
            fp = self.cat.get_path(self.tasks_folder, label)
            if self.options.building:
                if config.clean_fixmes:
                    task.export_fixmes(fp)
                report.fixme_stats(task, label)
                report.cons_stats(task_osm)
                report.osm_stats(task_osm)
            if self.split and os.path.exists(fp + ".osm.gz"):
                if not os.path.exists(self.bkp_path):
                    n = len(glob(fp + "*.osm.gz"))
                    label = f"{label}-{n}"
                    pa["localId"] = label
                    to_change[pa.id()] = geo.tools.get_attributes(pa)
            self.write_osm(task_osm, self.tasks_folder, label + ".osm.gz")
            del task
        if to_clean:
            self.parcel.writer.deleteFeatures(to_clean)
            log.debug(_("Removed %d void parcels"), len(to_clean))
        if to_change:
            self.parcel.writer.changeAttributeValues(to_change)
            log.debug(_("Conflict with %d existing tasks"), len(to_change))
        msg = _("Generated %d rustic and %d urban tasks files")
        log.debug(msg, tasks_r, tasks_u)
        report.tasks_r = tasks_r
        report.tasks_u = tasks_u

    def get_tasks(self, source):
        """Put each source feature into a task layer."""
        if os.path.exists(self.tasks_path):
            for fn in os.listdir(self.tasks_path):
                if os.path.isfile(fn):
                    os.remove(os.path.join(self.tasks_path, fn))
        tasks = {}
        layer_class = type(source)
        last_task = None
        to_add = []
        fcount = source.featureCount()
        for i, feat in enumerate(source.getFeatures()):
            localid = source.get_id(feat)
            label = self.tasks.get(localid, localid)
            if i == 0:
                last_task = label
            f = source.copy_feature(feat, {}, {})
            if i == fcount - 1 or label == last_task:
                to_add.append(f)
            if i == fcount - 1 or label != last_task:
                if last_task not in tasks:
                    tasks[last_task] = layer_class(baseName=last_task)
                    tasks[last_task].source_date = source.source_date
                tasks[last_task].writer.addFeatures(to_add)
                to_add = [f]
            last_task = label
        return tasks

    def get_zoning(self):
        """Get zoning data."""
        zoning_gml = self.cat.read("cadastralzoning")
        self.rustic_zoning = geo.ZoningLayer(baseName="rusticzoning")
        self.urban_zoning = geo.ZoningLayer(baseName="urbanzoning")
        q = lambda f, kw: self.urban_zoning.check_zone(f, kw["level"])
        if self.split or self.options.parcel:
            q = lambda f, kw: (
                self.urban_zoning.check_zone(f, kw["level"])
                and self.parcel_query(f, kw)
            )
        self.rustic_zoning.append(zoning_gml, query=q, level="P")
        self.urban_zoning.append(zoning_gml, query=q, level="M")
        del zoning_gml

    def get_boundary(self):
        """Get best boundary search area for overpass queries."""
        id = None
        fn = self.cat.get_path(self.cat.zip_code + ".geojson")
        if not os.path.exists(fn):
            id, name = boundary.get_municipality(self.cat.zip_code)
        if id is None:
            zoning_gml = self.cat.read("cadastralzoning")
            id, name = boundary.search_municipality(
                self.path, self.cat.zip_code, self.cat.cat_mun, zoning_gml.bounding_box()
            )
        if id is None:
            msg = _("Municipality code '%s' don't exists") % self.cat.zip_code
            raise CatValueError(msg)
        self.boundary_search_area = id
        report.mun_name = name
        log.info(_("Municipality: '%s'"), name)

    def output_zoning(self):
        """Generate project zoning file."""
        if not self.options.parcel:
            self.parcel.topology(dup_thr=20 * config.dup_thr)
            self.parcel.set_muncode(self.cat.zip_code)
            report.tasks = self.parcel.featureCount()
            self.export_layer(self.parcel, "zoning.geojson", target_crs_id=4326)
            fp = self.cat.get_path("zoning")
            with ZipFile(fp + ".zip", "w", ZIP_DEFLATED) as zf:
                zf.write(fp + ".geojson", "zoning.geojson")

    def export_poly(self):
        bpoly = geo.ZoningLayer()
        bpoly.append(self.rustic_zoning, level="P")
        bpoly.reproject()
        fn = self.cat.get_path("boundary.poly")
        bpoly.export_poly(fn)
        log.info(_("Generated '%s'"), fn)
        del bpoly

    def process_building(self):
        """Process all buildings dataset."""
        self.building.remove_outside_parts()
        self.building.remove_parts_wo_building()
        self.building.explode_multi_parts()
        self.building.clean()
        if log.app_level <= logging.DEBUG:
            fn = "building.geojson"
            self.export_layer(self.building, fn, "GeoJSON", target_crs_id=4326)
        if self.options.building:
            self.building.validate(report.max_level, report.min_level)

    def process_parcel(self):
        """Process parcels dataset."""
        self.parcel.set_zones(self.urban_zoning)
        self.parcel.set_zones(self.rustic_zoning)
        self.parcel.set_missing_zones()
        tasks1 = self.parcel.merge_by_adjacent_buildings(self.building)
        for k, v in self.tasks.items():
            self.tasks[k] = tasks1.get(v, v)
        tasks2 = self.parcel.merge_by_parts_count(
            config.parcel_parts, config.parcel_dist
        )
        for k, v in self.tasks.items():
            self.tasks[k] = tasks2.get(v, v)

    def finish(self):
        """Generate final report."""
        options = self.options
        if log.app_level > logging.DEBUG:
            geo.BaseLayer.delete_shp(self.cat.get_path("parcel.shp"))
            geo.BaseLayer.delete_shp(self.cat.get_path("building.shp"))
        if report.end_fixme_stats():
            log.warning(_("Check %d fixme tags"), report.fixme_count)
            fn = self.cat.get_path("review.txt")
            fixmes = report.get_tasks_with_fixmes()
            csvtools.dict2csv(fn, fixmes)
            msg = _("Please, check it before publish")
            log.info(_("Generated '%s'") + ". " + msg, fn)
        if options.building:
            report.cons_end_stats()
        else:
            report.clean_group("building")
        report.validate()
        report.to_file(self.cat.get_path("report.txt"))
        report.export(self.cat.get_path("report.json"))
        self.move_project()
        log.info(_("Finished!"))

    def exit(self):
        """Exit properly."""
        for propname in list(self.__dict__.keys()):
            if isinstance(getattr(self, propname), QgsVectorLayer):
                delattr(self, propname)

    def get_cbcn(self):
        """Read CartoBCN addresses."""
        reader = cbcn.Reader(self.aux_path)
        cbcn_src = reader.read()
        self.address = cbcn.get_address(cbcn_src, self.parcel)
        del cbcn_src
        report.inp_address = self.address.featureCount()
        report.inp_address_entrance = report.inp_address
        report.inp_address_parcel = 0
        self.address.remove_address_wo_building(self.building)
        report.inp_zip_codes = 0
        report.inp_street_names = self.address.count(unique="TN_text")
        if self.split or self.options.parcel:
            self.boundary_bbox = self.parcel.bounding_box()
        self.export_layer(self.address, "address.geojson", target_crs_id=4326)
        self.get_translations(self.address)

    def get_address(self):
        """Read Address GML dataset."""
        if self.cat.zip_code == "08900":
            self.get_cbcn()
            return
        address_gml = self.cat.read("address")
        report.address_date = address_gml.source_date
        if address_gml.writer.fieldNameIndex("component_href") == -1:
            address_gml = self.cat.read("address", force_zip=True)
            if address_gml.writer.fieldNameIndex("component_href") == -1:
                msg = (
                    _("Could not resolve joined tables for the '%s' layer")
                    % address_gml.name()
                )
                raise CatIOError(msg)
        self.address = geo.AddressLayer(source_date=address_gml.source_date)
        q = None
        if self.split or self.options.parcel:
            q = lambda f, kw: self.address.get_id(f) in kw["keys"]  # NOQA: E731
            self.boundary_bbox = self.parcel.bounding_box()
        self.address.append(address_gml, query=q, keys=self.tasks.keys())
        del address_gml
        report.inp_address = self.address.featureCount()
        report.inp_address_entrance = self.address.count("spec='Entrance'")
        report.inp_address_parcel = self.address.count("spec='Parcel'")
        self.get_auxiliary_addresses()
        self.address.remove_address_wo_building(self.building)
        if self.options.info:
            return
        if report.inp_address == 0:
            msg = _("No addresses data")
            if not self.options.building:
                raise CatValueError(msg)
            log.info(msg)
            return
        postaldescriptor = self.cat.read("postaldescriptor")
        thoroughfarename = self.cat.read("thoroughfarename")
        self.address.join_field(postaldescriptor, "PD_id", "gml_id", ["postCode"])
        self.address.join_field(thoroughfarename, "TN_id", "gml_id", ["text"], "TN_")
        del postaldescriptor, thoroughfarename
        report.inp_zip_codes = self.address.count(unique="postCode")
        report.inp_street_names = self.address.count(unique="TN_text")
        self.export_layer(self.address, "address.geojson", target_crs_id=4326)
        self.get_translations(self.address)

    def process_address(self):
        """Fix street names, conflate and move addresses."""
        highway_names = self.get_translations(self.address)
        ia = self.address.translate_field("TN_text", highway_names, copy_to="cat_name")
        if ia > 0:
            log.debug(_("Deleted %d addresses refused by street name"), ia)
            report.values["ignored_addresses"] = ia
        if not self.is_new and not self.options.manual:
            current_address = self.get_current_ad_osm()
            self.address.conflate(current_address)
        self.building.move_address(self.address)
        self.address.reproject()
        self.export_layer(self.address, "address_out.geojson")
        self.address_osm = self.address.to_osm()
        self.write_osm(self.address_osm, "address.osm")

    def stop_address(self):
        """Save current processing status and exits."""
        self.export_layer(self.parcel, "parcel.shp", driver_name="ESRI Shapefile")
        self.export_layer(self.building, "building.shp", driver_name="ESRI Shapefile")
        self.address.reproject()
        fn = self.cat.get_path("tasks.csv")
        csvtools.dict2csv(fn, self.tasks)
        report.to_file(self.cat.get_path("report.txt"))
        report.export(self.cat.get_path("report.json"))
        msg = _("Generated '%s'") % self.highway_names_path
        msg += ". " + _("Please, check it and run again")
        log.info(msg)

    def resume_address(self):
        """Resume processing for second run of addresses dataset."""
        report.from_file(self.cat.get_path("report.json"))
        fn = self.cat.get_path("tasks.csv")
        self.tasks = csvtools.csv2dict(fn, exists=True)
        fn = self.cat.get_path("parcel.shp")
        parcel = geo.ParcelLayer(self.cat.zip_code, fn, providerLib="ogr")
        if not parcel.isValid() or parcel.featureCount() == 0:
            raise CatValueError(_("No parcels data"))
        self.parcel = geo.ParcelLayer(self.cat.zip_code)
        self.parcel.append(parcel)
        del parcel
        fn = self.cat.get_path("building.shp")
        building = geo.ConsLayer(fn, providerLib="ogr")
        if not building.isValid() or building.featureCount() == 0:
            raise CatValueError(_("No buildings data"))
        self.building = geo.ConsLayer()
        self.building.append(building)
        del building
        fn = self.cat.get_path("address.geojson")
        address = geo.AddressLayer(fn, providerLib="ogr")
        if not address.isValid() or address.featureCount() == 0:
            raise CatValueError(_("No addresses data"))
        self.address = geo.AddressLayer()
        self.address.rename = {}
        self.address.resolve = {}
        self.address.append(address)
        self.address.reproject(self.building.crs())
        del address
        if self.split or self.options.parcel:
            self.boundary_bbox = self.parcel.bounding_box()

    def get_auxiliary_addresses(self):
        """Read and conflate auxiliary sources of addresses data."""
        for source in list(config.aux_address.keys()):
            if self.cat.zip_code[:2] in config.aux_address[source]:
                aux_source = globals()[source]
                reader = aux_source.Reader(self.aux_path)
                aux = reader.read(self.cat.zip_code[:2])
                aux_source.conflate(aux, self.address, self.cat.zip_code, self.split)

    def merge_address(self, building_osm, address_osm):
        """
        Copy address from address_osm to building_osm using 'ref' tag.

        If there exists one building with the same 'ref' that an address, copy
        the address tags to the building if it isn't a 'entrace' type address or
        else to the entrance if there exist a node with the address coordinates
        in the building.

        Precondition: building.move_address deleted addresses belonging to multiple
        buildings

        Args:
            building_osm (Osm): OSM data set with buildings
            address_osm (Osm): OSM data set with addresses
        """
        if "source:date" in address_osm.tags:
            building_osm.tags["source:date:addr"] = address_osm.tags["source:date"]
        address_index = defaultdict(list)
        building_index = defaultdict(list)
        for bu in building_osm.elements:
            if "ref" in bu.tags:
                building_index[bu.tags["ref"]].append(bu)
        for ad in address_osm.nodes:
            if ad.tags.get("ref", "") in building_index:
                address_index[ad.tags["ref"]].append(ad)
        md = 0
        for (ref, group) in list(building_index.items()):
            parcel_ad = []
            entrance_count = 0
            for ad in address_index[ref]:
                entrance = False
                if "entrance" in ad.tags:
                    for w in building_osm.get_outline(group):
                        entrance = w.search_node(ad.x, ad.y)
                        if entrance:
                            entrance.tags.update(ad.tags)
                            if not config.show_refs:
                                entrance.tags.pop("ref", None)
                            entrance.tags.pop("image", None)
                            break
                if entrance:
                    entrance_count += 1
                else:
                    parcel_ad.append(ad)
            if len(parcel_ad) == 1 and entrance_count == 0:
                ad = parcel_ad.pop()
                bu = group[0]
                bu.tags.update(ad.tags)
                bu.tags.pop("image", None)
                bu.tags.pop("entrance", None)
            md += len(parcel_ad)
        if md > 0:
            log.debug(_("Refused %d 'parcel' addresses not unique for it building"), md)
            report.inc("not_unique_addresses", md)

    def get_translations(self, address):
        """
        Get the translate file.

        If there exists the translation file 'highway_types.csv', read it,
        else write one with default values. If the translations file
        'highway_names.csv' don't exist, creates one parsing current OSM
        highways data, else reads and returns it as a dictionary.

        * 'highway_types.csv' List of osm elements in json format located in the
          application path that contains translations from abbreviations to full
          types of highways.

        * 'highway_names.csv' is located in the outputh folder and contains
          corrections for original highway names.
        """
        highway_types_path = os.path.join(config.app_path, "highway_types.csv")
        if not os.path.exists(highway_types_path):
            csvtools.dict2csv(highway_types_path, config.highway_types)
        else:
            csvtools.csv2dict(highway_types_path, config.highway_types)
        if self.is_new:
            if self.options.manual:
                highway = None
                place = None
            else:
                highway = self.get_highway()
                highway.reproject(address.crs())
                place = self.get_place()
                place.reproject(address.crs())
            highway_names = address.get_names(highway, place)
            csvtools.dict2csv(self.highway_names_path, highway_names, sort=1)
        else:
            highway_names = csvtools.csv2dict(self.highway_names_path, {})
        for key, value in list(highway_names.items()):
            v = value if isinstance(value, str) else value[0]
            highway_names[key] = v.strip()
        return highway_names

    def get_place(self):
        """Get OSM places for street names conflation."""
        ql = [
            'node["place"]["name"]',
            'way["place"]["name"]',
            'relation["place"]["name"]',
        ]
        place_osm = self.read_osm("current_place.osm", ql=ql)
        place = geo.PlaceLayer()
        place.read_from_osm(place_osm)
        del place_osm
        return place

    def get_highway(self):
        """Get OSM highways for street names conflation."""
        ql = [
            'way["highway"]["name"]',
            'relation["highway"]["name"]',
            'way["place"="square"]["name"]',
            'relation["place"="square"]["name"]',
        ]
        highway_osm = self.read_osm("current_highway.osm", ql=ql)
        highway = geo.HighwayLayer()
        highway.read_from_osm(highway_osm)
        del highway_osm
        return highway

    def get_current_ad_osm(self):
        """Get OSM address for conflation."""
        ql = [
            'node["addr:street"]["addr:housenumber"]["entrance"]',
            'wr["addr:street"]["addr:housenumber"][~"building"~".*"]',
            'nwr["addr:place"]["addr:housenumber"]',
        ]
        address_osm = self.read_osm("current_address.osm", ql=ql)
        current_address = set()
        w = 0
        report.osm_addresses = 0
        for d in address_osm.elements:
            if "addr:housenumber" not in d.tags:
                if "addr:street" in d.tags or "addr:place" in d.tags:
                    w += 1
            elif "addr:street" in d.tags:
                current_address.add(d.tags["addr:street"] + d.tags["addr:housenumber"])
                report.osm_addresses += 1
            elif "addr:place" in d.tags:
                current_address.add(d.tags["addr:place"] + d.tags["addr:housenumber"])
                report.osm_addresses += 1
        if w > 0:
            msg = _("There are %d address without house number in the OSM data") % w
            log.warning(msg)
            report.warnings.append(msg)
            report.osm_addresses_without_number = w
        return current_address

    def move_project(self):
        """
        Move to tasks all files needed for the backup the in the repository.

        Use a subdirectory if it's a split municipality.
        """
        if not os.path.exists(self.bkp_path):
            os.makedirs(self.bkp_path)
        move_files = [
            "current_address.osm",
            "current_highway.osm",
            "highway_names.csv",
            "tasks.csv",
        ]
        copy_files = [
            "address.osm",
            "address.geojson",
            "zoning.geojson",
            "zoning.zip",
            "report.txt",
            "review.txt",
            "report.json",
        ]
        if self.options.split:
            shutil.move(self.tasks_path, self.bkp_path)
        bkp_path = os.path.join(self.bkp_path, self.tasks_folder)
        if self.options.split:
            if self.options.split == report.get("split_id", " "):
                copy_files.append(report.split_name.replace(" ", "_") + ".osm")
            else:
                copy_files.append(self.options.split)
        for f in move_files:
            fn = self.cat.get_path(f)
            if os.path.exists(fn):
                os.rename(fn, os.path.join(bkp_path, f))
        for f in copy_files:
            fn = self.cat.get_path(f)
            if os.path.exists(fn):
                shutil.copy(fn, bkp_path)

    def export_layer(self, layer, filename, driver_name="GeoJSON", target_crs_id=None):
        """
        Export a vector layer.

        Args:
            layer (QgsVectorLayer): Source layer.
            filename (str): Output filename.
            driver_name (str): name of OGR driver (or get it from filename).
            target_crs_id (int): Defaults to source CRS.
        """
        out_path = self.cat.get_path(filename)
        if layer.export(out_path, driver_name, target_crs_id=target_crs_id):
            log.info(_("Generated '%s'"), filename)
        else:
            raise CatIOError(_("Failed to write layer: '%s'") % filename)

    def read_osm(self, *paths, **kwargs):
        """
        Read an OSM data set from an OSM XML file.

        If the file not exists, downloads data from overpass using ql query.

        Args:
            paths (str): input filename components relative to self.path
            ql (str): Query to put in the url for overpass

        Returns
            Osm: OSM data set
        """
        ql = kwargs.get("ql", False)
        osm_path = self.cat.get_path(*paths)
        filename = os.path.basename(osm_path)
        if not os.path.exists(osm_path):
            if not ql:
                return None
            log.info(_("Downloading '%s'") % filename)
            query = overpass.Query(self.boundary_search_area)
            if hasattr(self, "boundary_bbox") and self.boundary_bbox:
                query.set_search_area(self.boundary_bbox)
            query.add(ql)
            if log.app_level == logging.DEBUG:
                query.download(osm_path, log)
            else:
                query.download(osm_path)
        if osm_path.endswith(".gz"):
            fo = gzip.open(osm_path, "rb")
        else:
            fo = open(osm_path, "rb")
        data = osmxml.deserialize(fo)
        fo.close()
        if len(data.elements) == 0:
            msg = _("No OSM data were obtained from '%s'") % filename
            log.warning(msg)
            report.warnings.append(msg)
        else:
            log.info(
                _("Read '%s': %d nodes, %d ways, %d relations"),
                filename,
                len(data.nodes),
                len(data.ways),
                len(data.relations),
            )
        return data

    def write_osm(self, data, *paths):
        """
        Generate an OSM XML file for an OSM data set.

        Args:
            data (Osm): OSM data set
            paths (str): output filename components relative to self.path
                            (compress if ends with .gz)
        """
        if not config.show_refs:
            for e in data.elements:
                if "ref" in e.tags:
                    del e.tags["ref"]
        data.merge_duplicated()
        osm_path = self.cat.get_path(*paths)
        if osm_path.endswith(".gz"):
            file_obj = codecs.getwriter("utf-8")(gzip.open(osm_path, "w"))
        else:
            file_obj = io.open(osm_path, "w", encoding="utf-8")
        osmxml.serialize(file_obj, data)
        file_obj.close()
        msg = _("Generated '%s': %d nodes, %d ways, %d relations")
        log.info(
            msg,
            os.path.basename(osm_path),
            len(data.nodes),
            len(data.ways),
            len(data.relations),
        )
