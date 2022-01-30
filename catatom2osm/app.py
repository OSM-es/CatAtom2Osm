"""
Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files
"""
from __future__ import division
from builtins import map, object
from past.builtins import basestring
import io, codecs
import hashlib
import gzip
import logging
import os
import shutil
from collections import defaultdict
from glob import glob

from qgis.core import *
import qgis.utils

qgis.utils.uninstallErrorHook()
qgis_utils = getattr(qgis.utils, 'QGis', getattr(qgis.utils, 'Qgis', None))
from osgeo import gdal

from catatom2osm import config, catatom, csvtools, geo, osm, osmxml, overpass
from catatom2osm import cdau  # Used in get_auxiliary_addresses
from catatom2osm.report import instance as report

log = logging.getLogger(config.app_name)
if config.silence_gdal:
    gdal.PushErrorHandler('CPLQuietErrorHandler')

tasks_folder = 'tasks'


class QgsSingleton(QgsApplication):
    """Keeps a unique instance of QGIS for the application (and tests)"""
    _qgs = None

    def __new__(cls):
        if QgsSingleton._qgs is None:
            # Init qGis API
            QgsSingleton._qgs = QgsApplication([], False)
            qgis_prefix = os.getenv('QGISHOME')
            if qgis_prefix:
                QgsApplication.setPrefixPath(qgis_prefix, True)
            QgsApplication.initQgis()
            # sets GDAL to convert xlink references to fields but not resolve
            gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES')
            gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        return QgsSingleton._qgs


class CatAtom2Osm(object):
    """
    Main application class for a tool to convert the data sets from the
    Spanish Cadastre ATOM Services to OSM files.
    """

    def __init__(self, a_path, options):
        """
        Constructor.

        Args:
            a_path (str): Directory where the source files are located.
            options (dict): Dictionary of options.
        """
        self.options = options
        self.cat = catatom.Reader(a_path)
        self.path = self.cat.path
        self.zone = list(self.options.zone)
        report.clear(options=self.options.args, mun_code=self.cat.zip_code)
        report.sys_info = True
        if report.sys_info:
            report.qgs_version = qgis_utils.QGIS_VERSION
            report.gdal_version = gdal.__version__
            log.debug(_("Initialized QGIS %s API"), report.qgs_version)
            log.debug(_("Using GDAL %s"), report.gdal_version)
        if qgis_utils.QGIS_VERSION_INT < config.MIN_QGIS_VERSION_INT:
            msg = _(
                "Required QGIS version %s or greater") % config.MIN_QGIS_VERSION
            raise ValueError(msg)
        gdal_version_int = int('{:02d}{:02d}{:02d}'.format(
            *list(map(int, gdal.__version__.split('.')))))
        if gdal_version_int < config.MIN_GDAL_VERSION_INT:
            msg = _(
                "Required GDAL version %s or greater") % config.MIN_GDAL_VERSION
            raise ValueError(msg)
        self.highway_names_path = self.cat.get_path('highway_names.csv')
        self.tasks_path = self.cat.get_path(tasks_folder)
        if not os.path.exists(self.tasks_path):
            os.makedirs(self.tasks_path)
        self.split = None
        if self.options.split:
            self.split = geo.BaseLayer(
                self.options.split, 'zoningsplit', 'ogr'
            )
            if not self.split.isValid():
                raise IOError("Can't open %s" % self.options.split)
        self.is_new = not os.path.exists(self.highway_names_path)
        self.move = False

    @staticmethod
    def create_and_run(a_path, options):
        app = CatAtom2Osm(a_path, options)
        app.run()
        app.exit()

    def run(self):
        """Launches the app"""
        # -l --list
        if self.options.list_zones:
            self.list_zones()
            return
        # -c --comment
        elif self.options.comment:
            for folder in glob(self.tasks_path + '*'):
                self.add_comments(os.path.basename(folder))
            return
        log.info(_("Start processing '%s'"), report.mun_code)
        self.get_zoning()
        if self.options.zoning or not self.is_new:
            self.process_zoning()
        if self.options.zoning:
            self.output_zoning()
            self.end_messages()
            return
        # main process
        self.get_boundary()
        self.address_osm = osm.Osm()
        self.building_osm = osm.Osm()
        self.building_opt = self.options.building
        if self.options.address and self.is_new:
            self.options.building = False
        if self.building_opt:
            self.get_building()
        if self.options.address:
            self.read_address()
        if report.sum('inp_buildings', 'inp_address') == 0:
            self.end_messages()
            return
        if self.options.building:
            self.process_building()
        if self.options.address:
            self.address.reproject()
            self.address_osm = self.address.to_osm()
        # task processing
        if not (self.options.address and self.is_new):
            self.process_tasks(self.labels_layer)
        if self.options.address:
            self.write_osm(self.address_osm, 'address.osm')
            del self.address_osm
        self.output_zoning()
        if not self.is_new:
            self.move = True
        self.end_messages()

    def list_zones(self):
        zoning_gml = self.cat.read("cadastralzoning")
        labels = {
            geo.ZoningLayer.format_label(feat)
            for feat in zoning_gml.getFeatures()
        }
        for label in sorted(labels):
            print(label)

    def add_comments(self, folder):
        """Recover missing task files metadata after Josm editing."""
        report_path = self.cat.get_path(folder, 'report.txt')
        if not os.path.exists(report_path):
            return
        report.from_file(report_path)
        for fn in os.listdir(self.cat.get_path(folder)):
            if fn.endswith('.osm') or fn.endswith('.osm.gz'):
                label = os.path.basename(fn).split('.')[0]
                data = self.read_osm(folder, fn)
                fixmes = sum([1 for e in data.elements if 'fixme' in e.tags])
                if fixmes > 0:
                    log.warning(_("Check %d fixme tags"), fixmes)
                oldtags = dict(data.tags)
                data.tags.update(config.changeset_tags)
                comment = ' '.join((
                    config.changeset_tags['comment'],
                    report.mun_code,
                    report.mun_name, label
                ))
                data.tags['comment'] = comment
                data.tags['generator'] = report.app_version
                if 'building_date' in report.values:
                    data.tags['source:date'] = report.building_date
                if 'address_date' in report.values:
                    data.tags['source:date:addr'] = report.address_date
                if data.tags != oldtags:
                    self.write_osm(data, folder, fn)
        report.clear()

    def zone_query(self, feat, kwargs):
        """Filter feat by zone label if needed."""
        label = self.get_label(feat)
        if geo.AddressLayer.is_address(feat):
            if label is None:
                report.inc('orphand_addresses')
        if geo.ConsLayer.is_part(feat):
            if label is None:
                report.inc('orphand_parts')
        if len(self.zone) == 0:
            return label is not None
        return label in self.zone

    def get_label(self, feat):
        """Get the zone label for this feature from the index"""
        localid = geo.ConsLayer.get_id(feat)
        label = self.labels.get(localid, None)
        if label is None and not geo.AddressLayer.is_address(feat):
            label = self.labels.get(feat['localId'], None)
        return label


    def get_labels(self, main_gml, part_gml=None, other_gml=None):
        """Creates labels index"""
        fn = 'addr_labels.csv' if part_gml is None else 'cons_labels.csv'
        self.labels_layer = self.address if part_gml is None else self.building
        self.labels_path = self.cat.get_path(fn)
        labels = csvtools.csv2dict(self.labels_path)
        self.labels = labels
        if len(self.labels) > 0:
            return
        self.urban_zoning.get_labels(labels, main_gml)
        self.rustic_zoning.get_labels(labels, main_gml)
        if part_gml is not None:
            self.urban_zoning.get_labels(labels, part_gml)
            self.rustic_zoning.get_labels(labels, part_gml)
            if other_gml:
                self.urban_zoning.get_labels(labels, other_gml)
                self.rustic_zoning.get_labels(labels, other_gml)
        csvtools.dict2csv(self.labels_path, labels)

    def split_zoning(self):
        """Filter zoning using self.options.split."""
        self.urban_zoning.remove_outside_features(self.split, self.zone)
        self.rustic_zoning.remove_outside_features(self.split, self.zone)
        self.zone += [
            f['label']
            for f in self.rustic_zoning.getFeatures()
            if f['label'] not in self.zone
        ]
        self.zone += [
            f['label']
            for f in self.urban_zoning.getFeatures()
            if f['label'] not in self.zone
        ]
        if len(self.zone) == 0:
            msg = _("'%s' does not include any zone") % self.options.split
            raise ValueError(msg)
        del self.split


    def get_building(self):
        """Merge building, parts and pools"""
        building_gml = self.cat.read("building")
        part_gml = self.cat.read("buildingpart")
        other_gml = self.cat.read("otherconstruction", True)
        report.building_date = building_gml.source_date
        self.building = geo.ConsLayer(source_date=building_gml.source_date)
        self.get_labels(building_gml, part_gml, other_gml)
        if self.zone or self.split:
            self.split_zoning()
            self.get_bbox()
        self.building.append(building_gml, query=self.zone_query)
        report.inp_buildings = self.building.featureCount()
        if report.inp_buildings == 0:
            log.info(_("No building data"))
            return
        self.building.append(part_gml, query=self.zone_query)
        report.inp_parts = self.building.featureCount() - report.inp_buildings
        report.inp_pools = 0
        if other_gml:
            self.building.append(other_gml, query=self.zone_query)
            report.inp_pools = (
                self.building.featureCount()
                - report.inp_buildings
                - report.inp_parts
            )
        report.inp_features = self.building.featureCount()

    def process_tasks(self, source):
        """
        Convert shp to osm for each task.
        Remove zones without buildings (empty tasks).
        """
        tasks = self.get_tasks(source)
        exp = ''
        if len(self.zone) > 0:
            exp = "label IN (%s)" % ', '.join(["'%s'" % z for z in self.zone])
        zoning = [
            (self.rustic_zoning.format_label(zone), zone.id())
            for zone in self.rustic_zoning.search(exp)
        ]
        zoning += [
            (self.urban_zoning.format_label(zone), zone.id())
            for zone in self.urban_zoning.search(exp)
        ]
        if report.tasks_m > 0:
            zoning.append(('missing', None))
        to_clean = {'r': [], 'u': []}
        for label, fid in zoning:
            if label not in tasks:
                t = 'r' if len(label) == 3 else 'u'
                to_clean[t].append(fid)
        for label, task in tasks.items():
            comment = ' '.join((
                config.changeset_tags['comment'],
                report.mun_code,
                report.mun_name,
                label
            ))
            task.source_date = self.labels_layer.source_date
            task_osm = task.to_osm(upload='yes', tags={'comment': comment})
            if self.building_opt:
                self.merge_address(task_osm, self.address_osm)
            report.address_stats(task_osm)
            report.cons_stats(task_osm, label)
            self.write_osm(task_osm, tasks_folder, label + '.osm.gz')
            report.osm_stats(task_osm)
        no_data = len(to_clean['r']) + len(to_clean['u'])
        if no_data > 0:
            log.info(_("Removed %d zones without data"), no_data)
        if to_clean['r']:
            self.rustic_zoning.writer.deleteFeatures(to_clean['r'])
        if to_clean['u']:
            self.urban_zoning.writer.deleteFeatures(to_clean['u'])

    def get_tasks(self, source):
        """
        Put each building into a shp file named according to the field 'label'.
        """
        if os.path.exists(self.tasks_path):
            for fn in os.listdir(self.tasks_path):
                if os.path.isfile(fn):
                    os.remove(os.path.join(self.tasks_path, fn))
        tasks_m = 0
        last_task = None
        tasks = {}
        to_add = []
        fcount = source.featureCount()
        layer_class = type(self.labels_layer)
        for i, feat in enumerate(source.getFeatures()):
            label = self.get_label(feat) or 'missing'
            if i == 0:
                last_task = label
            f = source.copy_feature(feat, {}, {})
            if i == fcount - 1 or label == last_task:
                to_add.append(f)
            if i == fcount - 1 or label != last_task:
                if last_task == 'missing':
                    tasks_m += len(to_add)
                if last_task not in tasks:
                    tasks[last_task] = layer_class(baseName=last_task)
                tasks[last_task].writer.addFeatures(to_add)
                to_add = [f]
            last_task = label
        msg = _("Generated %d rustic and %d urban tasks files")
        tasks_r = len([l for l in tasks.keys() if len(l) == 3])
        tasks_u = len([l for l in tasks.keys() if len(l) == 5])
        log.debug(msg, tasks_r, tasks_u)
        if tasks_m > 0:
            msg = _(
                "There are %d buildings without zone, check %s"
            ) % (tasks_m, 'tasks/missing.osm')
            log.warning(msg)
            report.warnings.append(msg)
        report.tasks_r = tasks_r
        report.tasks_u = tasks_u
        report.tasks_m = tasks_m
        return tasks

    def get_zoning(self):
        """
        Reads cadastralzoning and splits in 'MANZANA' (urban) and 'POLIGONO'
        (rustic)
        """
        zoning_gml = self.cat.read("cadastralzoning")
        self.rustic_zoning = geo.ZoningLayer(baseName='rusticzoning')
        self.urban_zoning = geo.ZoningLayer(baseName='urbanzoning')
        self.rustic_zoning.append(zoning_gml, level='P')
        self.urban_zoning.append(zoning_gml, level='M')
        if len(self.zone) > 0:
            labels = [
                self.rustic_zoning.format_label(f)
                for f in self.rustic_zoning.getFeatures()
            ]
            labels += [
                self.urban_zoning.format_label(f)
                for f in self.urban_zoning.getFeatures()
            ]
            for zone in self.zone:
                if zone not in labels and zone !='missing':
                    msg = _("Zone '%s' does not exists") % zone
                    raise ValueError(msg)
        self.rustic_zoning.set_tasks(self.cat.zip_code)
        self.urban_zoning.set_tasks(self.cat.zip_code)

    def get_boundary(self):
        """Get best boundary search area for overpass queries."""
        fn = os.path.join(config.app_path, 'municipalities.csv')
        __, id, name = csvtools.get_key(fn, self.cat.zip_code)
        self.boundary_search_area = id
        report.mun_name = name
        report.cat_mun = self.cat.cat_mun
        log.info(_("Municipality: '%s'"), name)

    def get_bbox(self):
        self.rustic_zoning.selectByExpression(f"label in ({str(self.zone)[1:-1]})")
        bbox = self.rustic_zoning.boundingBoxOfSelected()
        self.urban_zoning.selectByExpression(f"label in ({str(self.zone)[1:-1]})")
        bbox.combineExtentWith(self.urban_zoning.boundingBoxOfSelected())
        if not bbox.isEmpty():
            self.boundary_bbox = self.urban_zoning.get_overpass_bbox(bbox)

    def process_zoning(self):
        self.rustic_zoning.clean()
        if self.urban_zoning.featureCount() > 0:
            self.urban_zoning.clean()

    def output_zoning(self):
        self.urban_zoning.reproject()
        self.rustic_zoning.reproject()
        if not self.zone:
            out_path = self.cat.get_path('boundary.poly')
            self.rustic_zoning.export_poly(out_path)
            log.info(_("Generated '%s'"), out_path)
        self.rustic_zoning.difference(self.urban_zoning)
        if not self.zone:
            self.export_layer(
                self.urban_zoning, 'urban_zoning.geojson', 'GeoJSON'
            )
            self.export_layer(
                self.rustic_zoning, 'rustic_zoning.geojson', 'GeoJSON'
            )
        self.rustic_zoning.append(self.urban_zoning)
        fn = 'zoning.geojson'
        self.export_layer(self.rustic_zoning, fn, 'GeoJSON')

    def process_building(self):
        """Process all buildings dataset"""
        self.building.remove_outside_parts()
        self.building.explode_multi_parts()
        self.building.clean()
        self.building.validate(report.max_level, report.min_level)
        if self.options.address:
            self.building.move_address(self.address)
        self.building.reproject()

    def output_building(self):
        self.building_osm = self.building.to_osm()
        self.delete_shp('building')
        if self.options.address:
            self.merge_address(self.building_osm, self.address_osm)
        self.write_osm(self.building_osm, 'building.osm')
        del self.building_osm

    def process_parcel(self):
        parcel_gml = self.cat.read("cadastralparcel")
        fn = self.cat.get_path('parcel.shp')
        geo.ParcelLayer.create_shp(fn, parcel_gml.crs())
        parcel = geo.ParcelLayer(
            fn, providerLib='ogr', source_date=parcel_gml.source_date
        )
        parcel.append(parcel_gml)
        del parcel_gml
        parcel.reproject()
        parcel_osm = parcel.to_osm()
        self.delete_shp(parcel)
        self.write_osm(parcel_osm, "parcel.osm")

    def end_messages(self):
        self.delete_shp('urban_zoning')
        self.delete_shp('rustic_zoning')
        self.delete_shp('address')
        self.delete_shp('building')
        options = self.options
        if report.fixme_stats():
            log.warning(_("Check %d fixme tags"), report.fixme_count)
            fn = 'review.txt'
            with open(self.cat.get_path(fn), "w") as fo:
                fixmes = report.get_tasks_with_fixmes()
                fo.write(config.eol.join(fixmes) + config.eol
                )
                log.info(
                    _("Generated '%s'") + '. ' + _("Please, check it"), fn
                )
        if options.building and not self.options.zoning:
            if report.get('out_buildings'):
                report.cons_end_stats()
        report.to_file(self.cat.get_path('report.txt'))
        if self.move:
            self.move_project()
        if (
            report.sum('inp_buildings', 'inp_address') == 0
            and not self.options.zoning
        ):
            msg = _("No data to process")
        elif self.options.address and self.is_new and not self.options.zoning:
            msg = _("Generated '%s'") % self.highway_names_path
            msg += '. ' + _("Please, check it and run again")
        else:
            msg = _("Finished!")
        log.info(msg)

    def exit(self):
        """Ends properly"""
        for propname in list(self.__dict__.keys()):
            if isinstance(getattr(self, propname), QgsVectorLayer):
                delattr(self, propname)

    def export_layer(self, layer, filename, driver_name='ESRI Shapefile',
                     target_crs_id=None):
        """
        Export a vector layer.

        Args:
            layer (QgsVectorLayer): Source layer.
            filename (str): Output filename.
            driver_name (str): Defaults to ESRI Shapefile.
            target_crs_id (int): Defaults to source CRS.
        """
        out_path = self.cat.get_path(filename)
        if layer.export(out_path, driver_name, target_crs_id=target_crs_id):
            log.info(_("Generated '%s'"), filename)
        else:
            raise IOError(_("Failed to write layer: '%s'") % filename)

    def read_osm(self, *paths, **kwargs):
        """
        Reads a OSM data set from a OSM XML file. If the file not exists,
        downloads data from overpass using ql query

        Args:
            paths (str): input filename components relative to self.path
            ql (str): Query to put in the url for overpass

        Returns
            Osm: OSM data set
        """
        ql = kwargs.get('ql', False)
        osm_path = self.cat.get_path(*paths)
        filename = os.path.basename(osm_path)
        if not os.path.exists(osm_path):
            if not ql:
                return None
            log.info(_("Downloading '%s'") % filename)
            query = overpass.Query(self.boundary_search_area)
            if hasattr(self, 'boundary_bbox') and self.boundary_bbox:
                query.set_search_area(self.boundary_bbox)
            query.add(ql)
            if log.app_level == logging.DEBUG:
                query.download(osm_path, log)
            else:
                query.download(osm_path)
        if osm_path.endswith('.gz'):
            fo = gzip.open(osm_path, 'rb')
        else:
            fo = open(osm_path, 'rb')
        data = osmxml.deserialize(fo)
        fo.close()
        if len(data.elements) == 0:
            msg = _("No OSM data were obtained from '%s'") % filename
            log.warning(msg)
            report.warnings.append(msg)
        else:
            log.info(_("Read '%s': %d nodes, %d ways, %d relations"),
                     filename, len(data.nodes), len(data.ways),
                     len(data.relations))
        return data

    def write_osm(self, data, *paths):
        """
        Generates a OSM XML file for a OSM data set.

        Args:
            data (Osm): OSM data set
            paths (str): output filename components relative to self.path
                            (compress if ends with .gz)
        """
        for e in data.elements:
            if 'ref' in e.tags:
                del e.tags['ref']
        data.merge_duplicated()
        osm_path = self.cat.get_path(*paths)
        if osm_path.endswith('.gz'):
            file_obj = codecs.getwriter("utf-8")(gzip.open(osm_path, "w"))
        else:
            file_obj = io.open(osm_path, "w", encoding="utf-8")
        osmxml.serialize(file_obj, data)
        file_obj.close()
        log.info(_("Generated '%s': %d nodes, %d ways, %d relations"),
                 os.path.basename(osm_path), len(data.nodes), len(data.ways),
                 len(data.relations))

    def read_address(self):
        """Reads Address GML dataset"""
        address_gml = self.cat.read("address")
        report.address_date = address_gml.source_date
        if address_gml.writer.fieldNameIndex('component_href') == -1:
            address_gml = self.cat.read("address", force_zip=True)
            if address_gml.writer.fieldNameIndex('component_href') == -1:
                msg = _("Could not resolve joined tables for the "
                        "'%s' layer") % address_gml.name()
                raise IOError(msg)
        self.address = geo.AddressLayer(source_date=address_gml.source_date)
        if not self.building_opt:
            self.get_labels(address_gml)
            if self.zone or self.split:
                self.split_zoning()
                self.get_bbox()
        self.address.append(address_gml, query=self.zone_query)
        report.inp_address = self.address.featureCount()
        if report.inp_address == 0:
            log.info(_("No addresses data"))
            return
        postaldescriptor = self.cat.read("postaldescriptor")
        thoroughfarename = self.cat.read("thoroughfarename")
        self.address.join_field(
            postaldescriptor, 'PD_id', 'gml_id', ['postCode']
        )
        self.address.join_field(
            thoroughfarename, 'TN_id', 'gml_id', ['text'], 'TN_'
        )
        report.inp_address_entrance = self.address.count("spec='Entrance'")
        report.inp_address_parcel = self.address.count("spec='Parcel'")
        report.inp_zip_codes = self.address.count(unique='postCode')
        report.inp_street_names = self.address.count(unique='TN_text')
        self.get_auxiliary_addresses()
        if self.building_opt:
            self.address.get_image_links()
        self.export_layer(
            self.address, 'address.geojson', 'GeoJSON', target_crs_id=4326
        )
        highway_names = self.get_translations(self.address)
        ia = self.address.translate_field('TN_text', highway_names)
        if ia > 0:
            log.debug(_("Deleted %d addresses refused by street name"), ia)
            report.values['ignored_addresses'] = ia
        if not self.is_new and not self.options.manual:
            current_address = self.get_current_ad_osm()
            self.address.conflate(current_address)

    def get_auxiliary_addresses(self):
        """If exists, reads and conflate an auxiliary addresses data source"""
        for source in list(config.aux_address.keys()):
            if self.cat.zip_code[:2] in config.aux_address[source]:
                aux_source = globals()[source]
                aux_path = os.path.join(
                    os.path.dirname(self.path), config.aux_path
                )
                reader = aux_source.Reader(aux_path)
                aux = reader.read(self.cat.zip_code[:2])
                aux_source.conflate(aux, self.address, self.cat.zip_code)

    def merge_address(self, building_osm, address_osm):
        """
        Copy address from address_osm to building_osm using 'ref' tag.

        If there exists one building with the same 'ref' that an address, copy
        the address tags to the building if it isn't a 'entrace' type address or
        else to the entrance if there exist a node with the address coordinates
        in the building.

        Precondition: building.move_address deleted addresses belonging to multiple buildings

        Args:
            building_osm (Osm): OSM data set with buildings
            address_osm (Osm): OSM data set with addresses
        """
        if 'source:date' in address_osm.tags:
            building_osm.tags['source:date:addr'] = address_osm.tags[
                'source:date']
        address_index = defaultdict(list)
        building_index = defaultdict(list)
        for bu in building_osm.elements:
            if 'ref' in bu.tags:
                building_index[bu.tags['ref']].append(bu)
        for ad in address_osm.nodes:
            if ad.tags['ref'] in building_index:
                address_index[ad.tags['ref']].append(ad)
        md = 0
        for (ref, group) in list(building_index.items()):
            parcel_ad = []
            entrance_count = 0
            for ad in address_index[ref]:
                entrance = False
                if 'entrance' in ad.tags:
                    for w in building_osm.get_outline(group):
                        entrance = w.search_node(ad.x, ad.y)
                        if entrance:
                            ad.tags['group'] = str(len(group))
                            entrance.tags.update(ad.tags)
                            entrance.tags.pop('ref', None)
                            entrance.tags.pop('image', None)
                            break
                if entrance:
                    entrance_count += 1
                else:
                    parcel_ad.append(ad)
            if len(parcel_ad) == 1 and entrance_count == 0:
                ad = parcel_ad.pop()
                bu = group[0]
                bu.tags.update(ad.tags)
                bu.tags.pop('image', None)
                bu.tags.pop('entrance', None)
            md += len(parcel_ad)
        if md > 0:
            log.debug(
                _("Refused %d 'parcel' addresses not unique for it building"),
                md)
            report.inc('not_unique_addresses', md)

    def get_translations(self, address):
        """
        If there exists the configuration file 'highway_types.csv', read it,
        else write one with default values. If don't exists the translations file
        'highway_names.csv', creates one parsing current OSM highways data, else
        reads and returns it as a dictionary.

        * 'highway_types.csv' List of osm elements in json format located in the
          application path that contains translations from abbreviations to full
          types of highways.

        * 'highway_names.csv' is located in the outputh folder and contains
          corrections for original highway names.
        """
        highway_types_path = os.path.join(config.app_path, 'highway_types.csv')
        if not os.path.exists(highway_types_path):
            csvtools.dict2csv(highway_types_path, config.highway_types)
        else:
            csvtools.csv2dict(highway_types_path, config.highway_types)
        if self.is_new:
            if self.options.manual:
                highway = None
            else:
                highway = self.get_highway()
                highway.reproject(address.crs())
            highway_names = address.get_highway_names(highway)
            csvtools.dict2csv(self.highway_names_path, highway_names, sort=1)
        else:
            highway_names = csvtools.csv2dict(self.highway_names_path, {})
        for key, value in list(highway_names.items()):
            highway_names[key] = value.strip()
        return highway_names

    def get_highway(self):
        """Gets OSM highways needed for street names conflation"""
        ql = ['way["highway"]["name"]',
              'relation["highway"]["name"]',
              'way["place"="square"]["name"]',
              'relation["place"="square"]["name"]']
        highway_osm = self.read_osm('current_highway.osm', ql=ql)
        highway = geo.HighwayLayer()
        highway.read_from_osm(highway_osm)
        del highway_osm
        return highway

    def get_current_ad_osm(self):
        """Gets OSM address for address conflation"""
        ql = ['node["addr:street"]["addr:housenumber"]',
              'way["addr:street"]["addr:housenumber"]',
              'relation["addr:street"]["addr:housenumber"]',
              'node["addr:place"]["addr:housenumber"]',
              'way["addr:place"]["addr:housenumber"]',
              'relation["addr:place"]["addr:housenumber"]']
        address_osm = self.read_osm('current_address.osm', ql=ql)
        current_address = set()
        w = 0
        report.osm_addresses = 0
        for d in address_osm.elements:
            if 'addr:housenumber' not in d.tags:
                if 'addr:street' in d.tags or 'addr:place' in d.tags:
                    w += 1
            elif 'addr:street' in d.tags:
                current_address.add(
                    d.tags['addr:street'] + d.tags['addr:housenumber'])
                report.osm_addresses += 1
            elif 'addr:place' in d.tags:
                current_address.add(
                    d.tags['addr:place'] + d.tags['addr:housenumber'])
                report.osm_addresses += 1
        if w > 0:
            msg = _(
                "There are %d address without house number in the OSM data") % w
            log.warning(msg)
            report.warnings.append(msg)
            report.osm_addresses_whithout_number = w
        return current_address

    def get_current_bu_osm(self):
        """Gets OSM buildings for building conflation"""
        ql = 'way[building];relation[building];way[leisure=swimming_pool];relation[leisure=swimming_pool]'
        current_bu_osm = self.read_osm('current_building.osm', ql=ql)
        return current_bu_osm

    def delete_shp(self, layer_or_name):
        if isinstance(layer_or_name, QgsVectorLayer):
            lyr = layer_or_name
        elif hasattr(self, layer_or_name):
            lyr = getattr(self, layer_or_name)
        else:
            return
        fn = lyr.writer.dataSourceUri().split('|')[0]
        is_shp = str(fn.lower().endswith('.shp'))
        if is_shp and not lyr.keep:
            geo.BaseLayer.delete_shp(fn)

    def move_project(self):
        """
        Move to tasks all files needed for the project for backup in the
        repository. Use a subdirectory if it's a split municipality.
        """
        bkp_dir = ''
        if self.options.split:
            fn = self.options.split
            bkp_dir = os.path.splitext(os.path.basename(fn))[0]
        elif len(self.zone) == 1:
            bkp_dir = self.zone[0]
        elif self.zone:
            bkp_dir = hashlib.sha224(
                str(self.zone).encode('utf-8')
            ).hexdigest()[:7]
        bkp_path = self.cat.get_path(tasks_folder, bkp_dir)
        if not os.path.exists(bkp_path):
            os.makedirs(bkp_path)
        prj_files = [
            'address.osm', 'address.geojson', 'current_address.osm',
            'current_building.osm', 'current_highway.osm', 'highway_names.csv',
            'report.txt', 'review.txt', 'rustic_zoning.geojson',
            'urban_zoning.geojson', 'zoning.geojson',
        ]
        for f in prj_files:
            fn = self.cat.get_path(f)
            if os.path.exists(fn):
                os.rename(fn, os.path.join(bkp_path, f))
        if self.options.split is not None:
            shutil.copy(self.options.split, bkp_path)
